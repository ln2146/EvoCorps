"""
In-Network 召回源

阶段2: 关注流召回 - 获取用户关注的人发布的帖子
"""

from typing import List
from ..types import PostCandidate, UserContext, FeedSource
from ..repositories.post_repository import PostRepository


class InNetworkSource:
    """
    In-Network 召回源

    对应 X 算法的 Thunder 组件，获取关注流帖子
    维系现有生态位，加固信息茧房
    """

    def __init__(self):
        self.post_repo = PostRepository()

    def retrieve(self, user_context: UserContext, max_candidates: int = 100) -> List[PostCandidate]:
        """
        召回关注流帖子

        Args:
            user_context: 用户上下文
            max_candidates: 最大候选数量

        Returns:
            标记为 IN_NETWORK 的候选帖子列表
        """
        if not user_context.followed_ids:
            return []

        # 获取关注作者的帖子
        rows = self.post_repo.get_posts_by_authors(list(user_context.followed_ids))

        candidates = []
        for row in rows[:max_candidates]:
            candidate = PostCandidate.from_db_row(row)
            candidate.source = FeedSource.IN_NETWORK
            candidate.is_followed_author = True
            candidates.append(candidate)

        return candidates
