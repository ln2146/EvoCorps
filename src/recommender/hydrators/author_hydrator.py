"""
作者数据水合器

阶段3: 补充作者信息（follower_count / influence_score）
"""

import logging
from typing import List
from ..types import PostCandidate
from ..repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


class AuthorHydrator:
    """
    作者数据水合器

    批量查询 users 表，将 follower_count 和 influence_score 写入
    PostCandidate.author_follower_count / author_influence_score，
    供 Stage 5 的 AuthorCredibilityScorer 使用。
    """

    def __init__(self):
        self.user_repo = UserRepository()

    def hydrate(self, candidates: List[PostCandidate]) -> List[PostCandidate]:
        """
        水合作者数据

        单次批量查询，避免 N+1 问题。数据库不可用时静默降级，不中断管道。

        Args:
            candidates: 候选帖子列表

        Returns:
            已填充作者特征的候选帖子列表
        """
        if not candidates:
            return candidates

        author_ids = list({c.author_id for c in candidates if c.author_id})
        profiles = self.user_repo.get_author_profiles_batch(author_ids)

        for candidate in candidates:
            profile = profiles.get(candidate.author_id)
            if profile:
                candidate.author_follower_count = profile['follower_count']
                candidate.author_influence_score = profile['influence_score']

        logger.debug(
            f"AuthorHydrator: hydrated {len(candidates)} candidates "
            f"from {len(profiles)} author profiles"
        )

        return candidates
