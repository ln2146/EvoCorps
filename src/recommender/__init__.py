"""
X-Algorithm 推荐系统模块

对齐 X 算法的 7 阶段推荐流程:
1. Query Hydration - 用户上下文补充
2. Candidate Sources - 双轨召回 (In-Network + Out-Network)
3. Candidate Hydration - 候选数据补充
4. Pre-Scoring Filters - 前置过滤
5. Scoring - 多层评分 (Weighted + Embedding + Diversity + OON)
6. Selection - Top-K 选择
7. Post-Selection Filters - 后置过滤
"""

from .feed_pipeline import FeedPipeline
from .config import RecommenderConfig
from .types import FeedRequest, FeedResponse, PostCandidate, UserContext, FeedSource

__all__ = [
    'FeedPipeline',
    'RecommenderConfig',
    'FeedRequest',
    'FeedResponse',
    'PostCandidate',
    'UserContext',
    'FeedSource',
]
