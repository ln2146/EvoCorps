"""
推荐系统类型定义

对齐 X 算法的数据结构，支持 7 阶段推荐流程
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Set
from enum import Enum
from pydantic import BaseModel, validator


class FeedSource(str, Enum):
    """帖子来源类型 - 对应 X 算法的双轨召回"""
    IN_NETWORK = "in_network"        # 关注流 (Thunder)
    OUT_NETWORK = "out_network"      # 热点流 (Phoenix Retrieval)
    NON_NEWS = "non_news"            # 非新闻内容


class PostCandidate(BaseModel):
    """
    候选帖子数据结构

    扩展自 Post，增加推荐系统所需的评分字段
    """
    # 基础字段 (来自数据库)
    post_id: str
    content: str
    summary: Optional[str] = None
    author_id: str
    created_at: Optional[str] = None
    num_likes: int = 0
    num_shares: int = 0
    num_comments: int = 0
    num_flags: int = 0
    original_post_id: Optional[str] = None
    is_news: bool = False
    news_type: Optional[str] = None
    status: str = "active"

    # Agent 响应相关
    is_agent_response: bool = False
    agent_role: Optional[str] = None
    agent_response_type: Optional[str] = None
    intervention_id: Optional[int] = None

    # 推荐系统计算字段
    age_steps: int = 0                              # 帖子年龄 (时间步)
    source: FeedSource = FeedSource.OUT_NETWORK     # 召回来源
    is_followed_author: bool = False                # 是否关注作者
    feed_segment: str = "secondary"                 # Feed 分段标记

    # 评分字段
    engagement_score: float = 0.0      # 互动分数
    freshness_score: float = 1.0       # 新鲜度分数
    embedding_score: float = 0.0       # Embedding 相似度分数
    weighted_score: float = 0.0        # 加权后分数
    diversity_penalty: float = 1.0     # 多样性惩罚系数
    oon_adjustment: float = 1.0        # Out-of-Network 调整系数

    # 作者特征字段（由 AuthorHydrator 在 Stage 3 填充）
    author_follower_count: Optional[int] = None
    author_influence_score: Optional[float] = None

    # 审核系统字段（由 moderation 系统写入）
    moderation_degradation_factor: float = 1.0
    moderation_label: Optional[str] = None

    final_score: float = 0.0           # 最终排序分数

    class Config:
        use_enum_values = True

    @validator('num_likes', 'num_shares', 'num_comments', 'num_flags', pre=True)
    def ensure_non_negative(cls, v):
        """确保计数字段非负"""
        return max(0, v or 0)

    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> "PostCandidate":
        """从数据库行创建 PostCandidate"""
        data = dict(row) if not isinstance(row, dict) else row
        return cls(
            post_id=str(data['post_id']),
            content=data.get('content', ''),
            summary=data.get('summary'),
            author_id=str(data.get('author_id', '')),
            created_at=str(data.get('created_at', '')) if data.get('created_at') else None,
            num_likes=data.get('num_likes', 0) or 0,
            num_shares=data.get('num_shares', 0) or 0,
            num_comments=data.get('num_comments', 0) or 0,
            num_flags=data.get('num_flags', 0) or 0,
            original_post_id=str(data['original_post_id']) if data.get('original_post_id') else None,
            is_news=bool(data.get('is_news', False)),
            news_type=data.get('news_type'),
            status=data.get('status', 'active') or 'active',
            is_agent_response=bool(data.get('is_agent_response', False)),
            agent_role=data.get('agent_role'),
            agent_response_type=data.get('agent_response_type'),
            intervention_id=data.get('intervention_id'),
            moderation_degradation_factor=float(data['moderation_degradation_factor']) if data.get('moderation_degradation_factor') is not None else 1.0,
            moderation_label=data.get('moderation_label'),
        )

    def to_post_dict(self) -> Dict[str, Any]:
        """转换为 Post.from_row 可接受的字典格式"""
        return {
            'post_id': self.post_id,
            'content': self.content,
            'summary': self.summary,
            'author_id': self.author_id,
            'created_at': self.created_at,
            'num_likes': self.num_likes,
            'num_shares': self.num_shares,
            'num_comments': self.num_comments,
            'num_flags': self.num_flags,
            'original_post_id': self.original_post_id,
            'is_news': self.is_news,
            'news_type': self.news_type,
            'status': self.status,
            'is_agent_response': self.is_agent_response,
            'agent_role': self.agent_role,
            'agent_response_type': self.agent_response_type,
            'intervention_id': self.intervention_id,
            'moderation_degradation_factor': self.moderation_degradation_factor,
            'moderation_label': self.moderation_label,
        }


@dataclass
class UserContext:
    """
    用户上下文信息

    在 Query Hydration 阶段填充，供后续阶段使用
    """
    user_id: str
    followed_ids: Set[str] = field(default_factory=set)
    blocked_ids: Set[str] = field(default_factory=set)
    muted_keywords: List[str] = field(default_factory=list)
    seen_post_ids: Set[str] = field(default_factory=set)
    recent_interactions: List[str] = field(default_factory=list)
    persona: Optional[str] = None
    persona_embedding: Optional[List[float]] = None


@dataclass
class FeedRequest:
    """Feed 请求参数"""
    user_id: str
    time_step: int
    feed_size: int = 10
    include_embedding_score: bool = True
    cold_start: bool = False  # 是否冷启动 (time_step == 0)


@dataclass
class FeedResponse:
    """Feed 响应结果"""
    posts: List[PostCandidate]
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def post_ids(self) -> List[str]:
        return [p.post_id for p in self.posts]

    @property
    def in_network_count(self) -> int:
        return sum(1 for p in self.posts if p.source == FeedSource.IN_NETWORK)

    @property
    def out_network_count(self) -> int:
        return sum(1 for p in self.posts if p.source == FeedSource.OUT_NETWORK)


@dataclass
class PipelineContext:
    """
    管道上下文

    在各阶段间传递数据
    """
    request: FeedRequest
    user_context: UserContext
    candidates: List[PostCandidate] = field(default_factory=list)
    post_timesteps: Dict[str, int] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    log_prefix: str = ""  # 日志前缀，用于多线程环境下追踪

    def add_metadata(self, key: str, value: Any):
        self.metadata[key] = value
