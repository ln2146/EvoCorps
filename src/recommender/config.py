"""
推荐系统配置定义

对齐 Notice.md 的评分公式和 X 算法的核心机制
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass
class ScoringWeights:
    """
    评分权重配置

    对齐 Notice.md: Score = w1*Likes + w2*Shares*2 + w3*Comments
    """
    w_likes: float = 1.0       # w1: 点赞权重
    w_shares: float = 2.0      # w2: 转发权重 (Notice.md 要求 ×2)
    w_comments: float = 1.0    # w3: 评论权重


@dataclass
class FreshnessConfig:
    """
    新鲜度衰减配置

    公式: freshness = max(min_freshness, 1.0 - decay_rate × age_steps)
    最终分数: (engagement + bias) × freshness
    """
    decay_rate: float = 0.1      # lambda: 每时间步衰减 10%
    min_freshness: float = 0.1   # 最小新鲜度，防止过度衰减
    bias: float = 180.0          # beta: 基础分数偏置


@dataclass
class DiversityConfig:
    """
    作者多样性惩罚配置

    防止单个水军账号刷屏，逼迫水军采用分布式账号矩阵
    公式: penalty = penalty_factor ^ author_position
    """
    enabled: bool = True
    penalty_factor: float = 0.7   # 同作者后续帖子的折扣系数
    min_penalty: float = 0.1      # 惩罚下限，防止分数完全归零
    max_same_author: int = 3      # 同一作者最多出现次数


@dataclass
class EmbeddingConfig:
    """
    Embedding 配置

    双层架构:
    - 本地层: sentence-transformers 轻量模型 (默认)
    - 云端层: OpenAI Embedding API (可选)
    """
    enabled: bool = True
    # 本地模型配置
    model_name: str = "paraphrase-MiniLM-L6-v2"  # 轻量模型，CPU 可跑
    # OpenAI 配置
    use_openai_embedding: bool = False           # 是否使用 OpenAI Embedding
    openai_model_name: str = None                # OpenAI 模型名 (None 使用默认)
    # 通用配置
    cache_embeddings: bool = True                # 缓存帖子 embedding
    embedding_weight: float = 0.3                # embedding 分数权重
    max_cache_size: int = 10000                  # 最大缓存条目数


@dataclass
class SourceConfig:
    """
    召回源配置

    双轨召回: In-Network (关注流) + Out-Network (热点流)
    """
    in_network_ratio: float = 0.5    # 关注流占比
    out_network_ratio: float = 0.5   # 热点流占比
    max_candidates_per_source: int = 100


@dataclass
class OONConfig:
    """
    Out-of-Network 评分调整配置

    调整热点流内容的分数
    """
    enabled: bool = True
    boost_factor: float = 1.0    # 热点流加成系数 (1.0 = 不调整)
    high_engagement_threshold: int = 50  # 高互动阈值


@dataclass
class AuthorCredibilityConfig:
    """作者信誉评分配置（基于 users.influence_score）"""
    enabled: bool = True
    high_credibility_threshold: float = 0.7   # 高信誉阈值
    low_credibility_threshold: float = 0.3    # 低信誉（疑似水军）阈值
    high_credibility_boost: float = 1.15      # 高信誉加成 (+15%)
    low_credibility_penalty: float = 0.75     # 低信誉惩罚 (-25%)
    default_influence_score: float = 0.5      # 水合失败时的默认值（中性）
    max_boost_factor: float = 1.3             # 最大加成上限
    min_penalty_factor: float = 0.5           # 最大惩罚下限


@dataclass
class FilterConfig:
    """
    过滤器配置
    """
    filter_taken_down: bool = True       # 过滤已下架帖子
    filter_blocked_authors: bool = True  # 过滤屏蔽作者
    filter_self_posts: bool = True       # 过滤自己的帖子
    filter_seen_posts: bool = False      # 过滤已曝光帖子 (默认关闭)
    min_content_length: int = 0          # 最小内容长度


@dataclass
class SelectionConfig:
    """
    选择器配置

    分层采样策略，对齐现有 get_feed 逻辑
    """
    # 新闻帖子采样
    news_top_k: int = 10           # 新闻 Top-K 池
    news_pick_n: int = 5           # 从 Top-K 中采样数量
    news_secondary_offset: int = 10  # 次级池起始位置
    news_secondary_top_k: int = 10   # 次级池大小
    news_secondary_pick_n: int = 3   # 次级池采样数量

    # 非新闻帖子采样
    non_news_top_k: int = 10       # 非新闻 Top-K 池
    non_news_pick_n: int = 2       # 非新闻采样数量

    include_ties: bool = True      # 包含边界并列项


@dataclass
class ParallelizationConfig:
    """
    并行化配置

    控制推荐系统的并行化行为
    """
    enabled: bool = True             # 是否启用并行化
    stage1_parallel: bool = True     # 并行 Stage 1 查询（UserActionHydrator）
    stage2_parallel: bool = True     # 并行 Stage 2 召回（In/Out Network）
    use_post_cache: bool = True      # 启用帖子时间步缓存
    max_workers: int = 4             # 线程池最大工作线程数


@dataclass
class RecommenderConfig:
    """
    推荐系统总配置

    整合所有子配置
    """
    enabled: bool = True
    scoring: ScoringWeights = field(default_factory=ScoringWeights)
    freshness: FreshnessConfig = field(default_factory=FreshnessConfig)
    diversity: DiversityConfig = field(default_factory=DiversityConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    source: SourceConfig = field(default_factory=SourceConfig)
    oon: OONConfig = field(default_factory=OONConfig)
    filter: FilterConfig = field(default_factory=FilterConfig)
    selection: SelectionConfig = field(default_factory=SelectionConfig)
    author_credibility: AuthorCredibilityConfig = field(default_factory=AuthorCredibilityConfig)
    parallelization: ParallelizationConfig = field(default_factory=ParallelizationConfig)

    @classmethod
    def from_dict(cls, config_dict: Optional[Dict[str, Any]] = None) -> "RecommenderConfig":
        """
        从字典创建配置

        支持部分配置覆盖，未指定的使用默认值
        """
        if not config_dict:
            return cls()

        def parse_dataclass(dc_cls, data: Optional[Dict] = None):
            if not data:
                return dc_cls()
            # 只取 dataclass 定义的字段
            valid_fields = {f.name for f in dc_cls.__dataclass_fields__.values()}
            filtered = {k: v for k, v in data.items() if k in valid_fields}
            return dc_cls(**filtered)

        return cls(
            enabled=config_dict.get('enabled', True),
            scoring=parse_dataclass(ScoringWeights, config_dict.get('scoring')),
            freshness=parse_dataclass(FreshnessConfig, config_dict.get('freshness')),
            diversity=parse_dataclass(DiversityConfig, config_dict.get('diversity')),
            embedding=parse_dataclass(EmbeddingConfig, config_dict.get('embedding')),
            source=parse_dataclass(SourceConfig, config_dict.get('source')),
            oon=parse_dataclass(OONConfig, config_dict.get('oon')),
            filter=parse_dataclass(FilterConfig, config_dict.get('filter')),
            selection=parse_dataclass(SelectionConfig, config_dict.get('selection')),
            author_credibility=parse_dataclass(AuthorCredibilityConfig, config_dict.get('author_credibility')),
            parallelization=parse_dataclass(ParallelizationConfig, config_dict.get('parallelization')),
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，用于序列化"""
        from dataclasses import asdict
        return {
            'enabled': self.enabled,
            'scoring': asdict(self.scoring),
            'freshness': asdict(self.freshness),
            'diversity': asdict(self.diversity),
            'embedding': asdict(self.embedding),
            'source': asdict(self.source),
            'oon': asdict(self.oon),
            'filter': asdict(self.filter),
            'selection': asdict(self.selection),
            'author_credibility': asdict(self.author_credibility),
            'parallelization': asdict(self.parallelization),
        }


# 默认配置实例
DEFAULT_CONFIG = RecommenderConfig()
