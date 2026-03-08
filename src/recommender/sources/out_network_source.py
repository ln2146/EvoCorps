"""
Out-of-Network 召回源

阶段2: 热点流召回 - 获取全局热门帖子
"""

from typing import List
from ..types import PostCandidate, UserContext, FeedSource
from ..repositories.post_repository import PostRepository


class OutNetworkSource:
    """
    Out-of-Network 召回源

    对应 X 算法的 Phoenix Retrieval 组件，获取热点流帖子
    打破信息茧房，进行跨生态位文化输出的唯一通道
    """

    def __init__(self):
        self.post_repo = PostRepository()

    def retrieve(
        self,
        user_context: UserContext,
        max_candidates: int = 100,
        time_step: int = None
    ) -> List[PostCandidate]:
        """
        召回热点流帖子

        Args:
            user_context: 用户上下文
            max_candidates: 最大候选数量
            time_step: 当前时间步（用于缓存，None 则不缓存）

        Returns:
            标记为 OUT_NETWORK 的候选帖子列表
        """
        candidates = []
        followed_set = user_context.followed_ids

        # 获取新闻帖子（使用时间步缓存）
        news_rows = self.post_repo.get_active_news_posts_cached(time_step)
        for row in news_rows:
            candidate = PostCandidate.from_db_row(row)
            author_id = str(row.get('author_id', ''))

            # 如果是关注的作者，标记为 IN_NETWORK
            if author_id in followed_set:
                candidate.source = FeedSource.IN_NETWORK
                candidate.is_followed_author = True
            else:
                candidate.source = FeedSource.OUT_NETWORK
                candidate.is_followed_author = False

            candidates.append(candidate)

        # 获取非新闻帖子（使用时间步缓存）
        non_news_rows = self.post_repo.get_active_non_news_posts_cached(time_step)
        for row in non_news_rows:
            candidate = PostCandidate.from_db_row(row)
            author_id = str(row.get('author_id', ''))

            if author_id in followed_set:
                candidate.source = FeedSource.IN_NETWORK
                candidate.is_followed_author = True
            else:
                candidate.source = FeedSource.OUT_NETWORK
                candidate.is_followed_author = False

            candidates.append(candidate)

        return candidates[:max_candidates]
