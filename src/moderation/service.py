"""
审核服务核心

遵循 AGENT_ENVIRONMENT_SPEC.md: Service 层协调业务逻辑
"""

import asyncio
import logging
import os
from collections import Counter
from datetime import datetime
from typing import List, Optional, Dict, Any

from .types import (
    ModerationVerdict,
    ModerationAction,
    ModerationSeverity,
    ModerationStats,
)
from .config import ModerationConfig
from .providers import CompositeProvider
from .actions import (
    VisibilityDegradationAction,
    WarningLabelAction,
    HardTakedownAction,
)
from .repository import get_repository


logger = logging.getLogger(__name__)

# 专属审核审计日志记录器
_moderation_logger = None


def _get_moderation_logger():
    """
    获取或创建审核日志记录器，输出到 logs/moderation/

    日志架构：
    - FileHandler 挂在 `moderation` 父级 logger 上
    - 所有 `moderation.*` 子 logger（service、providers）的日志自动传播到父级
    - 这样 keyword_provider 和 llm_provider 的详细日志也会写入同一文件
    """
    global _moderation_logger
    if _moderation_logger is None:
        log_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            'logs', 'moderation'
        )
        os.makedirs(log_dir, exist_ok=True)

        log_file = os.path.join(log_dir, f'moderation_{datetime.now().strftime("%Y%m%d")}.log')

        # 父级 logger：接收所有 moderation.* 子 logger 的传播日志
        parent_logger = logging.getLogger('moderation')
        parent_logger.setLevel(logging.DEBUG)  # 捕获 DEBUG 及以上级别

        if not parent_logger.handlers:
            fh = logging.FileHandler(log_file, encoding='utf-8')
            fh.setLevel(logging.DEBUG)  # 文件记录所有详细日志
            # 格式包含 logger 名称，便于区分来源（service/keyword_provider/llm_provider）
            fh.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
            parent_logger.addHandler(fh)

        # 子 logger 用于 audit 专用的高层摘要日志
        _moderation_logger = logging.getLogger('moderation.audit')
        _moderation_logger.setLevel(logging.INFO)
        # 不再单独添加 handler，日志传播到父级 moderation logger

    return _moderation_logger


class ModerationService:
    """
    审核服务核心

    职责:
    1. 接收待审核内容
    2. 调用审核提供者
    3. 根据配置确定干预动作
    4. 执行干预动作
    5. 记录审核结果
    """

    def __init__(self, config: ModerationConfig = None):
        """
        初始化审核服务

        Args:
            config: 审核配置
        """
        self.config = config or ModerationConfig()
        self.repository = get_repository()
        self.provider = None
        self.actions = {}

        # 统计
        self.stats = ModerationStats()

        # 初始化组件
        self._init_components()

    def _init_components(self):
        """初始化提供者和动作"""
        # 提前初始化日志器，确保 provider 初始化日志也被捕获
        _get_moderation_logger()

        # 初始化提供者
        if self.config.enabled:
            self.provider = CompositeProvider(self.config)
            logger.info("Composite moderation provider initialized")

        # 初始化动作
        self.actions = {
            ModerationAction.VISIBILITY_DEGRADATION: VisibilityDegradationAction(
                self.config.actions
            ),
            ModerationAction.WARNING_LABEL: WarningLabelAction(
                self.config.actions
            ),
            ModerationAction.HARD_TAKEDOWN: HardTakedownAction(
                self.config.actions
            ),
        }

        logger.info(f"ModerationService initialized (enabled={self.config.enabled})")

    def _ensure_provider_initialized(self):
        """
        惰性初始化 Provider。

        当 control_flags.moderation_enabled 在服务创建后才被打开时，
        self.provider 仍为 None（因为初始化时 config.enabled=False）。
        调用此方法可在运行时补全初始化，保证审核功能正常启动。
        """
        if self.provider is not None:
            return
        self.provider = CompositeProvider(self.config)
        logger.info("Composite moderation provider lazily initialized (control_flags enabled after service creation)")

    def check_post(
        self,
        post_id: str,
        user_id: str,
        content: str,
        metadata: Dict[str, Any] = None,
        keyword_only: bool = False
    ) -> Optional[ModerationVerdict]:
        """
        检查单个帖子

        Args:
            post_id: 帖子 ID
            user_id: 用户 ID
            content: 帖子内容
            metadata: 额外元数据
            keyword_only: 是否只使用关键词审核（发布前）

        Returns:
            审核裁决，None 表示不需要干预
        """
        # 动态检查 control_flags.moderation_enabled
        import control_flags
        if not control_flags.moderation_enabled:
            raise RuntimeError(f"ModerationService is not enabled but check_post() was called for post {post_id}")
        if not self.provider:
            self._ensure_provider_initialized()

        mod_log = _get_moderation_logger()
        content_preview = (content or '').replace('\n', ' ')[:80]
        engagement = (metadata or {}).get('num_likes', 0) + (metadata or {}).get('num_shares', 0)
        check_type = "KEYWORD" if keyword_only else "LLM"
        mod_log.info(
            f"[{check_type}_CHECK] post={post_id} | user={user_id} | "
            f"engagement={engagement} | content=\"{content_preview}\""
        )

        # 更新统计
        self.stats.total_checked += 1

        # 1. 调用审核提供者
        verdict = self.provider.check(content, metadata, keyword_only=keyword_only)

        if verdict is None:
            mod_log.info(f"  [PASS] post={post_id} | no action required")
            return None

        # 填充基础信息
        verdict.post_id = post_id
        verdict.user_id = user_id

        # 2. 确定干预动作
        action = self._determine_action(verdict)

        if action == ModerationAction.NONE:
            mod_log.info(f"  [PASS] post={post_id} | flagged but below action threshold")
            return None

        verdict.action = action

        # 3. 设置动作参数
        self._setup_action_params(verdict)

        # 4. 执行干预动作
        success = self._execute_action(verdict)

        if success:
            # 5. 记录
            self.repository.save(verdict)

            # 更新统计
            self.stats.total_flagged += 1
            self.stats.action_counts[action] = (
                self.stats.action_counts.get(action, 0) + 1
            )
            self.stats.severity_counts[verdict.severity] = (
                self.stats.severity_counts.get(verdict.severity, 0) + 1
            )
            self.stats.category_counts[verdict.category] = (
                self.stats.category_counts.get(verdict.category, 0) + 1
            )

            mod_log.info(
                f"  [VERDICT] post={post_id} | "
                f"action={action.value} | "
                f"severity={verdict.severity} | "
                f"category={verdict.category} | "
                f"confidence={verdict.confidence:.2f}"
            )
            if action == ModerationAction.VISIBILITY_DEGRADATION:
                mod_log.info(
                    f"  [DEGRADATION] post={post_id} | "
                    f"factor={getattr(verdict, 'degradation_factor', 'N/A')}"
                )
            elif action == ModerationAction.WARNING_LABEL:
                mod_log.info(
                    f"  [LABEL] post={post_id} | "
                    f"text={getattr(verdict, 'label_text', 'N/A')}"
                )
            elif action == ModerationAction.HARD_TAKEDOWN:
                mod_log.info(f"  [TAKEDOWN] post={post_id} | user={user_id} | content removed")

            logger.info(
                f"Moderation action executed: post={post_id}, "
                f"action={action.value}, severity={verdict.severity}, "
                f"category={verdict.category}"
            )

        return verdict

    def check_batch(self, posts: List[Dict[str, Any]], keyword_only: bool = False) -> List[ModerationVerdict]:
        """
        批量检查帖子

        Args:
            posts: 帖子字典列表，每个包含 post_id, user_id, content
            keyword_only: 是否只使用关键词审核

        Returns:
            裁决列表
        """
        # 动态检查 control_flags.moderation_enabled
        import control_flags
        if not control_flags.moderation_enabled:
            raise RuntimeError("ModerationService is not enabled but check_batch() was called")
        if not self.provider:
            self._ensure_provider_initialized()

        mod_log = _get_moderation_logger()
        check_type = "KEYWORD" if keyword_only else "LLM"
        mod_log.info(f"[{check_type}_BATCH_START] posts_to_check={len(posts)}")

        verdicts = []

        for post in posts:
            verdict = self.check_post(
                post_id=post.get("post_id"),
                user_id=post.get("user_id") or post.get("author_id"),
                content=post.get("content", ""),
                metadata=post,
                keyword_only=keyword_only,
            )
            if verdict:
                verdicts.append(verdict)

        # 批次汇总
        # use_enum_values=True 使 verdict 字段已是字符串，无需 .value
        action_counts = Counter(v.action for v in verdicts)
        category_counts = Counter(v.category for v in verdicts)
        mod_log.info(
            f"[{check_type}_BATCH_END] checked={len(posts)} | flagged={len(verdicts)} | "
            f"actions={dict(action_counts)} | categories={dict(category_counts)}"
        )
        logger.info(f"Batch moderation completed ({check_type}): {len(verdicts)} actions taken")
        return verdicts

    def check_posts(
        self,
        posts: List[Dict[str, Any]],
        min_engagement: int = None,
        use_keyword_only: bool = False
    ) -> List[ModerationVerdict]:
        """
        检查帖子（分层审核策略）

        Args:
            posts: 帖子列表
            min_engagement: 最小互动数阈值（None 时使用 llm_check_threshold）
            use_keyword_only: 是否只使用关键词审核（发布前检查）

        Returns:
            裁决列表
        """
        # 动态检查 control_flags.moderation_enabled，而不是静态配置
        import control_flags
        is_enabled = control_flags.moderation_enabled

        mod_log = _get_moderation_logger()

        if not is_enabled:
            logger.warning(f"⚠️ Moderation service is DISABLED - skipping {len(posts)} posts (set moderation_enabled=True to enable)")
            return []

        if not self.provider:
            self._ensure_provider_initialized()

        # 分层审核逻辑
        if use_keyword_only:
            # 发布前：只用关键词审核
            threshold = self.config.keyword_check_threshold
            mod_log.info(f"[KEYWORD_CHECK] checking {len(posts)} posts at publish time")
        else:
            # 发布后：使用 LLM 审核
            threshold = min_engagement if min_engagement is not None else self.config.llm_check_threshold
            mod_log.info(f"[LLM_CHECK] checking posts with engagement >= {threshold}")

        # 过滤出需要检查的帖子
        posts_to_check = [
            post for post in posts
            if (post.get("num_likes", 0) + post.get("num_shares", 0)) >= threshold
        ]

        mod_log.info(
            f"[POST_CHECK] total_posts={len(posts)} | threshold={threshold} | "
            f"eligible={len(posts_to_check)} | skipped={len(posts) - len(posts_to_check)}"
        )

        if not posts_to_check:
            logger.info(f"No posts meet engagement threshold {threshold} (total posts: {len(posts)})")
            return []

        logger.info(f"🔍 Moderation checking {len(posts_to_check)} posts (threshold={threshold}, keyword_only={use_keyword_only})")
        return self.check_batch(posts_to_check, keyword_only=use_keyword_only)

    # 保持向后兼容的别名
    def check_news_posts(
        self,
        posts: List[Dict[str, Any]],
        min_engagement: int = None
    ) -> List[ModerationVerdict]:
        """
        检查新闻帖子（向后兼容别名，实际调用 check_posts）

        Args:
            posts: 帖子列表
            min_engagement: 最小互动数阈值

        Returns:
            裁决列表
        """
        return self.check_posts(posts, min_engagement)

    def _determine_action(self, verdict: ModerationVerdict) -> ModerationAction:
        """
        根据严重程度和置信度确定动作

        Args:
            verdict: 审核裁决

        Returns:
            应采取的动作
        """
        # 检查硬性打击阈值
        for severity, threshold in self.config.actions.takedown_thresholds.items():
            if verdict.severity == severity and verdict.confidence >= threshold:
                return ModerationAction.HARD_TAKEDOWN

        # 使用配置的映射
        return self.config.actions.severity_to_action.get(
            verdict.severity,
            ModerationAction.NONE
        )

    def _setup_action_params(self, verdict: ModerationVerdict):
        """
        设置动作参数

        Args:
            verdict: 审核裁决
        """
        if verdict.action == ModerationAction.VISIBILITY_DEGRADATION:
            verdict.degradation_factor = self.config.actions.visibility_degradation_factors.get(
                verdict.severity, 0.5
            )

        elif verdict.action == ModerationAction.WARNING_LABEL:
            category = verdict.category
            verdict.label_text = self.config.actions.warning_labels.get(
                category,
                self.config.actions.warning_labels.get("other", "⚠️ 此内容需谨慎参考")
            )

    def _execute_action(self, verdict: ModerationVerdict) -> bool:
        """
        执行干预动作

        Args:
            verdict: 审核裁决

        Returns:
            是否执行成功
        """
        action_executor = self.actions.get(verdict.action)

        if not action_executor:
            raise RuntimeError(f"No executor for action: {verdict.action}")

        return action_executor.execute(verdict)

    def get_stats(self) -> ModerationStats:
        """获取审核统计"""
        return self.stats

    def reset_stats(self):
        """重置统计"""
        self.stats = ModerationStats()

    def get_post_verdicts(self, post_id: str) -> List[ModerationVerdict]:
        """获取帖子的所有审核记录"""
        return self.repository.get_by_post_id(post_id)

    def get_user_verdicts(self, user_id: str, limit: int = 100) -> List[ModerationVerdict]:
        """获取用户的审核记录"""
        return self.repository.get_by_user_id(user_id, limit)

    def is_user_banned(self, user_id: str) -> bool:
        """检查用户是否被封禁"""
        takedown_action = self.actions.get(ModerationAction.HARD_TAKEDOWN)
        if takedown_action:
            return takedown_action.check_user_banned(user_id)
        return False

    def revert_action(self, post_id: str) -> bool:
        """
        撤销帖子的审核动作

        Args:
            post_id: 帖子 ID

        Returns:
            是否成功
        """
        # 获取最新的审核记录
        verdicts = self.repository.get_by_post_id(post_id)

        if not verdicts:
            raise RuntimeError(f"No moderation record found for post {post_id}")

        latest_verdict = verdicts[0]

        # 根据动作类型执行撤销
        if latest_verdict.action == ModerationAction.VISIBILITY_DEGRADATION:
            return self.actions[ModerationAction.VISIBILITY_DEGRADATION].revert(post_id)

        elif latest_verdict.action == ModerationAction.WARNING_LABEL:
            return self.actions[ModerationAction.WARNING_LABEL].revert(post_id)

        elif latest_verdict.action == ModerationAction.HARD_TAKEDOWN:
            return self.actions[ModerationAction.HARD_TAKEDOWN].restore_post(post_id)

        raise RuntimeError(f"Unknown moderation action type: {latest_verdict.action} for post {post_id}")


# 单例实例
_service_instance: Optional[ModerationService] = None


def get_service(config: ModerationConfig = None) -> ModerationService:
    """
    获取审核服务单例

    Args:
        config: 配置，首次调用时使用

    Returns:
        审核服务实例
    """
    global _service_instance
    if _service_instance is None:
        _service_instance = ModerationService(config)
    return _service_instance


def reset_service():
    """重置服务单例"""
    global _service_instance
    _service_instance = None
