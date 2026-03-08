"""
Feed 推荐管道

对应 X 算法的 Home Mixer，编排 7 阶段推荐流程
"""

import asyncio
import logging
import os
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import ClassVar, List, Optional

from .types import (
    FeedRequest, FeedResponse, UserContext, PostCandidate,
    PipelineContext, FeedSource
)
from .config import RecommenderConfig
from .repositories.post_repository import PostRepository
from .query_hydrators import UserActionHydrator, UserFeaturesHydrator
from .sources import InNetworkSource, OutNetworkSource
from .hydrators import CoreDataHydrator, AuthorHydrator
from .filters import PreScoringFilters, PostSelectionFilters
from .filters.moderation_filter import ModerationFilter
from .scorers import WeightedScorer, EmbeddingScorer, AuthorDiversityScorer, OONScorer, AuthorCredibilityScorer
from .selectors import TopKSelector

logger = logging.getLogger(__name__)

# 创建专门的推荐算法详细日志记录器
_pipeline_logger = None
_pipeline_logger_lock = threading.Lock()
_pipeline_write_lock = threading.Lock()


class _BufferedPipelineLogger:
    """线程内日志缓冲器：先收集本次 pipeline 日志，末尾统一刷盘。"""

    def __init__(self):
        self.lines: List[str] = []

    def info(self, message: str):
        self.lines.append(str(message))


def _get_pipeline_logger():
    """获取或创建推荐管道详细日志记录器（只写入文件，不输出到终端）"""
    global _pipeline_logger
    if _pipeline_logger is None:
        with _pipeline_logger_lock:
            if _pipeline_logger is None:
                log_dir = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                    'logs', 'recommender'
                )
                os.makedirs(log_dir, exist_ok=True)

                log_file = os.path.join(log_dir, f'pipeline_{datetime.now().strftime("%Y%m%d")}.log')
                log_file_abs = os.path.abspath(log_file)

                _pipeline_logger = logging.getLogger('recommender.pipeline')
                _pipeline_logger.setLevel(logging.INFO)
                _pipeline_logger.propagate = False  # 阻止日志传播到父 logger（不在终端显示）

                formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
                file_handlers = [
                    h for h in _pipeline_logger.handlers
                    if isinstance(h, logging.FileHandler)
                ]

                # 只保留一个指向当天日志文件的 FileHandler，清理重复 handler
                keep = None
                for h in file_handlers:
                    if os.path.abspath(getattr(h, 'baseFilename', '')) == log_file_abs:
                        keep = h
                        break
                for h in file_handlers:
                    if h is keep:
                        continue
                    _pipeline_logger.removeHandler(h)
                    h.close()

                if keep is None:
                    keep = logging.FileHandler(log_file, encoding='utf-8')
                    keep.setLevel(logging.INFO)
                    keep.setFormatter(formatter)
                    _pipeline_logger.addHandler(keep)

    return _pipeline_logger


class FeedPipeline:
    """
    Feed 推荐管道

    对应 X 算法的 Home Mixer，编排 7 阶段推荐流程:
    1. Query Hydration - 用户上下文补充
    2. Candidate Sources - 双轨召回
    3. Candidate Hydration - 候选数据补充
    4. Pre-Scoring Filters - 前置过滤
    5. Scoring - 多层评分
    6. Selection - Top-K 选择
    7. Post-Selection Filters - 后置过滤

    支持并行化优化:
    - Stage 2 双轨召回并行执行
    - 异步 execute_async() 方法
    """

    # 类级别线程池（用于 Stage 2 并行召回）
    _source_executor: ClassVar[ThreadPoolExecutor] = None
    _stage2_parallel: ClassVar[bool] = True
    _log_local: ClassVar[threading.local] = threading.local()

    def __init__(self, config: RecommenderConfig = None):
        """
        初始化管道

        Args:
            config: 推荐系统配置，为 None 时使用默认配置
        """
        self.config = config or RecommenderConfig()
        self._init_stages()

    @classmethod
    def configure_parallel(cls, stage2_parallel: bool = True):
        """
        配置并行化参数

        Args:
            stage2_parallel: 是否启用 Stage 2 并行召回
        """
        cls._stage2_parallel = stage2_parallel

    @classmethod
    def _get_source_executor(cls) -> ThreadPoolExecutor:
        """获取或创建 Stage 2 线程池（惰性初始化）"""
        if cls._source_executor is None and cls._stage2_parallel:
            cls._source_executor = ThreadPoolExecutor(max_workers=2)
        return cls._source_executor

    @property
    def pipeline_log(self):
        """返回当前线程的日志器（优先缓冲器，其次真实文件 logger）"""
        buffered = getattr(self._log_local, 'buffered_logger', None)
        if buffered is not None:
            return buffered
        return _get_pipeline_logger()

    def _begin_pipeline_log_buffer(self):
        """开始本线程 pipeline 日志缓冲。"""
        self._log_local.buffered_logger = _BufferedPipelineLogger()

    def _flush_pipeline_log_buffer(self):
        """将本线程缓冲日志按顺序一次性写入文件。"""
        buffered = getattr(self._log_local, 'buffered_logger', None)
        if buffered is None:
            return
        real_logger = _get_pipeline_logger()
        with _pipeline_write_lock:
            for line in buffered.lines:
                real_logger.info(line)
        self._log_local.buffered_logger = None

    def _init_stages(self):
        """初始化管道各阶段组件"""
        # 应用并行化配置
        para_config = self.config.parallelization
        if para_config.enabled:
            # 配置 Stage 1 并行查询
            UserActionHydrator.configure_parallel(
                enabled=para_config.stage1_parallel,
                max_workers=para_config.max_workers
            )
            # 配置 Stage 2 并行召回
            FeedPipeline.configure_parallel(
                stage2_parallel=para_config.stage2_parallel
            )

        # 数据仓库
        self.post_repo = PostRepository()

        # Stage 1: Query Hydrators
        self.user_action_hydrator = UserActionHydrator()
        self.user_features_hydrator = UserFeaturesHydrator()

        # Stage 2: Sources
        self.in_network_source = InNetworkSource()
        self.out_network_source = OutNetworkSource()

        # Stage 3: Hydrators
        self.core_data_hydrator = CoreDataHydrator()
        self.author_hydrator = AuthorHydrator()

        # Stage 4: Pre-Scoring Filters
        self.pre_scoring_filters = PreScoringFilters()

        # Stage 5: Scorers
        self.weighted_scorer = WeightedScorer(self.config.scoring)
        self.embedding_scorer = None
        if self.config.embedding.enabled:
            self.embedding_scorer = EmbeddingScorer(self.config.embedding)
            # NO FALLBACK: Require embedding_manager to be initialized if embedding is enabled
            if not self.embedding_scorer.embedding_manager:
                raise RuntimeError(
                    "RecommenderConfig.embedding.enabled=True but EmbeddingScorer.embedding_manager is None. "
                    "Either disable embedding in config or ensure dependencies are properly installed."
                )
            self.user_features_hydrator.set_embedding_manager(
                self.embedding_scorer.embedding_manager
            )
        self.diversity_scorer = AuthorDiversityScorer(self.config.diversity)
        self.oon_scorer = OONScorer(self.config.oon)
        self.credibility_scorer = AuthorCredibilityScorer(self.config.author_credibility)

        # Stage 6: Selector
        self.selector = TopKSelector(self.config.selection)

        # Stage 7: Post-Selection Filters
        self.post_selection_filters = PostSelectionFilters()

        # Moderation Filter (applied after selection)
        self.moderation_filter = ModerationFilter()

    def execute(self, request: FeedRequest) -> FeedResponse:
        """
        执行完整推荐管道

        Args:
            request: Feed 请求

        Returns:
            Feed 响应
        """
        self._begin_pipeline_log_buffer()
        try:
            plog = self.pipeline_log
            start_time = datetime.now()
            uid = request.user_id[:8]  # 用户 ID 短格式，用于日志前缀

            plog.info(f"[{uid}] {'=' * 50}")
            plog.info(f"[{uid}] [PIPELINE START] time_step={request.time_step}")

            logger.debug(f"Executing feed pipeline for user {request.user_id}")

            ctx = self._create_context(request)

            # Stage 1: Query Hydration
            t0 = datetime.now()
            ctx = self._stage1_query_hydration(ctx)
            d1 = (datetime.now() - t0).total_seconds()
            plog.info(
                f"[{uid}] [Stage 1: Query Hydration] "
                f"persona={ctx.user_context.persona or 'N/A'} | "
                f"followed={len(ctx.user_context.followed_ids)} | "
                f"blocked={len(ctx.user_context.blocked_ids)} | "
                f"muted_kw={len(ctx.user_context.muted_keywords)} | "
                f"duration={d1:.3f}s"
            )
            logger.debug(f"Stage 1: User context hydrated, followed={len(ctx.user_context.followed_ids)}")

            # Stage 2: Candidate Sources
            t0 = datetime.now()
            ctx = self._stage2_candidate_retrieval(ctx)
            d2 = (datetime.now() - t0).total_seconds()
            in_count = ctx.metadata.get('in_network_count', 0)
            out_count = ctx.metadata.get('out_network_count', 0)
            in_target = ctx.metadata.get('in_network_target', in_count)
            out_target = ctx.metadata.get('out_network_target', out_count)
            in_ratio = ctx.metadata.get('source_in_ratio', 0.5)
            out_ratio = ctx.metadata.get('source_out_ratio', 0.5)
            source_budget = ctx.metadata.get('source_total_budget', len(ctx.candidates))
            in_retrieved = ctx.metadata.get('in_network_retrieved', in_count)
            out_retrieved = ctx.metadata.get('out_network_retrieved', out_count)
            plog.info(
                f"[{uid}] [Stage 2: Candidate Retrieval] "
                f"total={len(ctx.candidates)}, in_network={in_count}, "
                f"out_network={out_count}, duration={d2:.3f}s | "
                f"ratio_target={in_ratio:.2f}/{out_ratio:.2f} | "
                f"quota={in_target}/{out_target} (budget={source_budget}) | "
                f"retrieved_raw={in_retrieved}/{out_retrieved}"
            )
            for c in ctx.candidates:
                plog.info(
                    f"[{uid}]   [CANDIDATE] post={c.post_id[:8]} | "
                    f"src={str(c.source):<13} | "
                    f"is_news={str(c.is_news):<5} | "
                    f"type={c.news_type or 'N/A':<4} | "
                    f"author={c.author_id} | "
                    f"likes={c.num_likes} shares={c.num_shares}"
                )
            logger.debug(f"Stage 2: Retrieved {len(ctx.candidates)} candidates")

            # Stage 3: Candidate Hydration
            t0 = datetime.now()
            ctx = self._stage3_data_hydration(ctx)
            d3 = (datetime.now() - t0).total_seconds()
            plog.info(f"[{uid}] [Stage 3: Data Hydration] candidates_hydrated={len(ctx.candidates)}, duration={d3:.3f}s")
            for c in ctx.candidates:
                if c.author_influence_score is not None:
                    plog.info(
                        f"[{uid}]   [AUTHOR] post={c.post_id[:8]} | "
                        f"author={c.author_id} | "
                        f"influence={c.author_influence_score:.3f} | "
                        f"followers={c.author_follower_count or 0}"
                    )
            logger.debug(f"Stage 3: Data hydration complete")

            # Stage 4: Pre-Scoring Filters
            t0 = datetime.now()
            before_filter = len(ctx.candidates)
            ctx = self._stage4_pre_scoring_filter(ctx)
            d4 = (datetime.now() - t0).total_seconds()
            filtered_out = before_filter - len(ctx.candidates)
            plog.info(
                f"[{uid}] [Stage 4: Pre-Scoring Filters] "
                f"before={before_filter}, after={len(ctx.candidates)}, "
                f"filtered_out={filtered_out}, duration={d4:.3f}s"
            )
            logger.debug(f"Stage 4: {len(ctx.candidates)} candidates after filtering")

            # Stage 5: Scoring
            t0 = datetime.now()
            ctx = self._stage5_scoring(ctx)
            d5 = (datetime.now() - t0).total_seconds()
            top_scores = [
                f"{c.post_id[:8]}:{c.final_score:.3f}"
                for c in sorted(ctx.candidates, key=lambda x: x.final_score, reverse=True)[:5]
            ]
            plog.info(
                f"[{uid}] [Stage 5: Scoring] "
                f"candidates_scored={len(ctx.candidates)}, "
                f"top5=[{', '.join(top_scores)}], duration={d5:.3f}s"
            )
            logger.debug(f"Stage 5: Scoring complete")

            # Stage 6: Selection
            t0 = datetime.now()
            before_selection = len(ctx.candidates)
            ctx = self._stage6_selection(ctx)
            d6 = (datetime.now() - t0).total_seconds()
            plog.info(
                f"[{uid}] [Stage 6: Selection] "
                f"before={before_selection}, selected={len(ctx.candidates)}, duration={d6:.3f}s"
            )
            logger.debug(f"Stage 6: Selected {len(ctx.candidates)} candidates")

            # Stage 7: Post-Selection Filters
            t0 = datetime.now()
            before_post = len(ctx.candidates)
            ctx = self._stage7_post_selection_filter(ctx)
            d7 = (datetime.now() - t0).total_seconds()
            post_filtered = before_post - len(ctx.candidates)
            import control_flags
            moderation_status = "enabled" if control_flags.moderation_enabled else "disabled"
            plog.info(
                f"[{uid}] [Stage 7: Post-Selection Filters] "
                f"before={before_post}, final={len(ctx.candidates)}, "
                f"filtered={post_filtered}, moderation={moderation_status}, duration={d7:.3f}s"
            )
            logger.debug(f"Stage 7: Final {len(ctx.candidates)} candidates")

            total_duration = (datetime.now() - start_time).total_seconds()
            plog.info(
                f"[{uid}] [PIPELINE END] "
                f"final_feed_size={len(ctx.candidates)}, total_duration={total_duration:.3f}s"
            )
            plog.info(f"[{uid}] {'-' * 50}")

            return self._build_response(ctx)
        finally:
            self._flush_pipeline_log_buffer()

    def _create_context(self, request: FeedRequest) -> PipelineContext:
        """创建管道上下文"""
        post_timesteps = self.post_repo.get_post_timesteps()
        return PipelineContext(
            request=request,
            user_context=UserContext(user_id=request.user_id),
            candidates=[],
            post_timesteps=post_timesteps,
            log_prefix=f"[{request.user_id[:8]}]",  # 用户 ID 短格式作为日志前缀
        )

    def _stage1_query_hydration(self, ctx: PipelineContext) -> PipelineContext:
        """阶段1: 查询水合 - 获取用户上下文"""
        ctx.user_context = self.user_action_hydrator.hydrate(ctx.request.user_id)
        ctx.user_context = self.user_features_hydrator.hydrate(ctx.user_context)
        return ctx

    def _stage2_candidate_retrieval(self, ctx: PipelineContext) -> PipelineContext:
        """阶段2: 候选召回 - 双轨召回（支持并行）"""
        source_cfg = self.config.source
        total_budget = max(1, int(source_cfg.max_candidates_per_source))
        in_target, out_target, in_ratio, out_ratio = self._compute_source_targets(
            total_budget=total_budget,
            in_ratio_raw=source_cfg.in_network_ratio,
            out_ratio_raw=source_cfg.out_network_ratio
        )

        if self._stage2_parallel:
            # 并行召回
            in_network, out_network = self._stage2_parallel_retrieve(
                ctx.user_context, total_budget, ctx.request.time_step
            )
        else:
            # 串行召回
            in_network = self.in_network_source.retrieve(
                ctx.user_context,
                max_candidates=total_budget
            )
            out_network = self.out_network_source.retrieve(
                ctx.user_context,
                max_candidates=total_budget,
                time_step=ctx.request.time_step
            )

        selected_in, selected_out = self._apply_source_ratio_budget(
            in_candidates=in_network,
            out_candidates=out_network,
            in_target=in_target,
            out_target=out_target,
            total_budget=total_budget,
            in_ratio=in_ratio,
            out_ratio=out_ratio
        )
        ctx.candidates = selected_in + selected_out

        ctx.add_metadata('source_total_budget', total_budget)
        ctx.add_metadata('source_in_ratio', in_ratio)
        ctx.add_metadata('source_out_ratio', out_ratio)
        ctx.add_metadata('in_network_target', in_target)
        ctx.add_metadata('out_network_target', out_target)
        ctx.add_metadata('in_network_retrieved', len(in_network))
        ctx.add_metadata('out_network_retrieved', len(out_network))
        ctx.add_metadata('in_network_count', len(selected_in))
        ctx.add_metadata('out_network_count', len(selected_out))

        return ctx

    @staticmethod
    def _compute_source_targets(
        total_budget: int,
        in_ratio_raw: float,
        out_ratio_raw: float
    ) -> tuple:
        """归一化 in/out ratio 并计算召回目标配额。"""
        in_ratio = max(0.0, float(in_ratio_raw or 0.0))
        out_ratio = max(0.0, float(out_ratio_raw or 0.0))

        ratio_sum = in_ratio + out_ratio
        if ratio_sum <= 0:
            in_ratio, out_ratio = 0.5, 0.5
        else:
            in_ratio /= ratio_sum
            out_ratio /= ratio_sum

        in_target = int(round(total_budget * in_ratio))
        out_target = total_budget - in_target

        # 正比率的来源至少分配 1 个配额
        if in_ratio > 0 and in_target == 0:
            in_target = 1
            out_target = max(0, total_budget - in_target)
        if out_ratio > 0 and out_target == 0:
            out_target = 1
            in_target = max(0, total_budget - out_target)

        return in_target, out_target, in_ratio, out_ratio

    @staticmethod
    def _apply_source_ratio_budget(
        in_candidates: List[PostCandidate],
        out_candidates: List[PostCandidate],
        in_target: int,
        out_target: int,
        total_budget: int,
        in_ratio: float,
        out_ratio: float
    ) -> tuple:
        """按配额选取候选，单侧不足时由另一侧补位。"""
        selected_in = list(in_candidates[:in_target])
        selected_out = list(out_candidates[:out_target])

        remaining_in = list(in_candidates[in_target:])
        remaining_out = list(out_candidates[out_target:])

        # 先处理目标来源不足场景
        if len(selected_in) < in_target and remaining_out:
            need = min(in_target - len(selected_in), len(remaining_out))
            selected_out.extend(remaining_out[:need])
            remaining_out = remaining_out[need:]

        if len(selected_out) < out_target and remaining_in:
            need = min(out_target - len(selected_out), len(remaining_in))
            selected_in.extend(remaining_in[:need])
            remaining_in = remaining_in[need:]

        # 若仍未达到总预算，按配置比率高的一侧优先补齐
        fill_order = (
            [('in', remaining_in), ('out', remaining_out)]
            if in_ratio >= out_ratio
            else [('out', remaining_out), ('in', remaining_in)]
        )

        while len(selected_in) + len(selected_out) < total_budget:
            progressed = False
            for source_name, pool in fill_order:
                if not pool:
                    continue
                candidate = pool.pop(0)
                if source_name == 'in':
                    selected_in.append(candidate)
                else:
                    selected_out.append(candidate)
                progressed = True
                if len(selected_in) + len(selected_out) >= total_budget:
                    break
            if not progressed:
                break

        return selected_in, selected_out

    def _stage2_parallel_retrieve(
        self,
        user_context: UserContext,
        max_candidates: int,
        time_step: int
    ) -> tuple:
        """
        并行执行双轨召回

        Args:
            user_context: 用户上下文
            max_candidates: 每个来源的最大候选数
            time_step: 当前时间步

        Returns:
            (in_network_candidates, out_network_candidates)
        """
        executor = self._get_source_executor()
        if executor is None:
            # 降级为串行
            in_network = self.in_network_source.retrieve(
                user_context, max_candidates
            )
            out_network = self.out_network_source.retrieve(
                user_context, max_candidates, time_step
            )
            return in_network, out_network

        # 提交并行任务
        in_future = executor.submit(
            self.in_network_source.retrieve,
            user_context,
            max_candidates
        )
        out_future = executor.submit(
            self.out_network_source.retrieve,
            user_context,
            max_candidates,
            time_step
        )

        # 等待结果
        in_network = in_future.result()
        out_network = out_future.result()

        return in_network, out_network

    def _stage3_data_hydration(self, ctx: PipelineContext) -> PipelineContext:
        """阶段3: 数据水合 - 补充候选数据"""
        ctx.candidates = self.core_data_hydrator.hydrate(
            ctx.candidates,
            ctx.post_timesteps,
            ctx.request.time_step
        )
        ctx.candidates = self.author_hydrator.hydrate(ctx.candidates)
        return ctx

    def _stage4_pre_scoring_filter(self, ctx: PipelineContext) -> PipelineContext:
        """阶段4: 预评分过滤（带审计日志）"""
        plog = self.pipeline_log

        candidates, audit = self.pre_scoring_filters.filter_with_audit(
            ctx.candidates,
            ctx.user_context,
            self.config.filter
        )
        ctx.candidates = candidates

        if audit:
            reason_counts = Counter(entry['reason'] for entry in audit)
            for entry in audit:
                plog.info(
                    f"  [FILTERED] post={entry['post_id'][:8]} | "
                    f"reason={entry['reason']:<20} | "
                    f"author={entry['author_id']}"
                )
            plog.info(
                f"  [FILTER_SUMMARY] " +
                " | ".join(f"{r}={c}" for r, c in sorted(reason_counts.items()))
            )

        return ctx

    def _stage5_scoring(self, ctx: PipelineContext) -> PipelineContext:
        """阶段5: 评分（带完整评分表日志）"""
        plog = self.pipeline_log
        uid = ctx.log_prefix

        # 5.1 基础加权评分
        ctx.candidates = self.weighted_scorer.score(
            ctx.candidates,
            self.config.freshness
        )

        # 5.2 Embedding 评分 (可选)
        if self.embedding_scorer and ctx.request.include_embedding_score:
            ctx.candidates = self.embedding_scorer.score(
                ctx.candidates,
                ctx.user_context
            )

        # 5.3 OON 评分
        ctx.candidates = self.oon_scorer.score(ctx.candidates)

        # 5.35 作者信誉调整
        ctx.candidates = self.credibility_scorer.score(ctx.candidates)

        # 5.4 作者多样性惩罚
        ctx.candidates = self.diversity_scorer.apply_penalty(ctx.candidates)

        # 完整评分表（按 final_score 降序）
        plog.info(f"{uid}   [SCORING_DETAIL] Showing all {len(ctx.candidates)} candidates sorted by final_score:")
        for rank, c in enumerate(sorted(ctx.candidates, key=lambda x: x.final_score, reverse=True), 1):
            src_tag = str(c.source).split('.')[-1] if '.' in str(c.source) else str(c.source)
            src_tag = src_tag[:3].upper()
            news_tag = f"news/{c.news_type or 'N/A'}" if c.is_news else "non-news"
            cred_tag = f"cred={c.author_influence_score:.2f}" if c.author_influence_score else "cred=N/A"
            plog.info(
                f"{uid}   [SCORE] rank={rank:2d} | post={c.post_id[:8]} | "
                f"weighted={c.weighted_score:7.2f} | "
                f"fresh={c.freshness_score:.2f} | "
                f"embed={c.embedding_score:.3f} | "
                f"oon={c.oon_adjustment:.2f} | "
                f"{cred_tag} | "
                f"div={c.diversity_penalty:.2f} | "
                f"final={c.final_score:7.3f} | "
                f"{src_tag} | {news_tag}"
            )

        return ctx

    def _stage6_selection(self, ctx: PipelineContext) -> PipelineContext:
        """阶段6: 选择（带每个入选帖子的日志和选择原因）"""
        plog = self.pipeline_log
        uid = ctx.log_prefix
        before_count = len(ctx.candidates)
        ctx.candidates = self.selector.select(ctx.candidates)

        # 统计各 segment 入选数量
        segment_counts = {}
        for c in ctx.candidates:
            segment_counts[c.feed_segment] = segment_counts.get(c.feed_segment, 0) + 1

        plog.info(f"{uid}   [SELECTION_SUMMARY] segments={dict(segment_counts)}")

        for rank, c in enumerate(ctx.candidates, 1):
            src_tag = str(c.source).split('.')[-1] if '.' in str(c.source) else str(c.source)
            src_tag = src_tag[:3].upper()
            news_tag = f"news/{c.news_type or 'N/A'}" if c.is_news else "non-news"

            # 选择原因
            reasons = []
            if c.feed_segment == "primary":
                reasons.append("high_score")
            else:
                reasons.append("diversity")
            if c.is_followed_author:
                reasons.append("followed")
            if c.is_news:
                reasons.append(f"type:{c.news_type or 'unknown'}")
            reason_str = "+".join(reasons) if reasons else "default"

            plog.info(
                f"{uid}   [SELECTED] rank={rank:2d} | "
                f"post={c.post_id[:8]} | "
                f"segment={c.feed_segment:<9} | "
                f"score={c.final_score:7.3f} | "
                f"author={c.author_id[:8]} | "
                f"{news_tag:<14} | {src_tag} | "
                f"reason={reason_str}"
            )

        return ctx

    def _stage7_post_selection_filter(self, ctx: PipelineContext) -> PipelineContext:
        """阶段7: 后选择过滤（带审核降级/移除日志）"""
        plog = self.pipeline_log
        uid = ctx.log_prefix
        before_count = len(ctx.candidates)
        ctx.candidates = self.post_selection_filters.filter(ctx.candidates)

        import control_flags
        if control_flags.moderation_enabled:
            # 在审核前快照分数和 ID，用于对比
            before_scores = {c.post_id: c.final_score for c in ctx.candidates}
            before_ids = {c.post_id for c in ctx.candidates}

            ctx.candidates = self.moderation_filter.filter(ctx.candidates)

            after_ids = {c.post_id for c in ctx.candidates}

            # 记录每个帖子的审核状态
            plog.info(f"{uid}   [MOD:CHECK] Checking {before_count} posts for moderation:")

            passed_count = 0
            degraded_count = 0
            removed_count = 0

            for c in ctx.candidates:
                old_score = before_scores.get(c.post_id, c.final_score)
                if c.final_score < old_score - 0.001:
                    # 被降级
                    degraded_count += 1
                    plog.info(
                        f"{uid}   [MOD:DEGRADED] post={c.post_id[:8]} | "
                        f"factor={c.moderation_degradation_factor:.2f} | "
                        f"score {old_score:.3f}->{c.final_score:.3f} | "
                        f"label={c.moderation_label or 'none'}"
                    )
                else:
                    # 通过审核
                    passed_count += 1
                    plog.info(
                        f"{uid}   [MOD:PASS] post={c.post_id[:8]} | "
                        f"factor={c.moderation_degradation_factor:.2f} | "
                        f"score={c.final_score:.3f} | "
                        f"label={c.moderation_label or 'none'}"
                    )

            # 记录被移除的帖子
            for post_id in before_ids - after_ids:
                removed_count += 1
                plog.info(f"{uid}   [MOD:REMOVED] post={post_id[:8]}")

            # 汇总统计
            plog.info(
                f"{uid}   [MOD:SUMMARY] total_checked={before_count} | "
                f"passed={passed_count} | degraded={degraded_count} | removed={removed_count}"
            )
        else:
            plog.info(f"{uid}   [MOD:SKIP] moderation disabled")

        return ctx

    def _build_response(self, ctx: PipelineContext) -> FeedResponse:
        """构建响应"""
        return FeedResponse(
            posts=ctx.candidates,
            metadata=ctx.metadata
        )

    async def execute_async(self, request: FeedRequest) -> FeedResponse:
        """
        异步执行推荐管道

        使用 asyncio.to_thread 将同步的 execute() 方法包装为异步，
        避免阻塞事件循环，实现跨用户并行处理。

        Args:
            request: Feed 请求

        Returns:
            Feed 响应
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.execute, request)


def create_pipeline(config_dict: dict = None) -> FeedPipeline:
    """
    工厂函数: 从配置字典创建管道

    Args:
        config_dict: 配置字典

    Returns:
        FeedPipeline 实例
    """
    config = RecommenderConfig.from_dict(config_dict)
    return FeedPipeline(config)
