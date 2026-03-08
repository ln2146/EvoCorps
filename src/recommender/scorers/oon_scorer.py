"""
Out-of-Network 评分器

阶段5: 调整热点流内容的分数
"""

from typing import List
from ..types import PostCandidate, FeedSource
from ..config import OONConfig


class OONScorer:
    """
    Out-of-Network 评分器

    调整热点流内容的分数，可以加成或惩罚
    """

    def __init__(self, config: OONConfig = None):
        self.config = config or OONConfig()

    def score(self, candidates: List[PostCandidate]) -> List[PostCandidate]:
        """
        调整 Out-of-Network 帖子分数

        Args:
            candidates: 候选帖子列表

        Returns:
            调整后的候选帖子列表
        """
        if not self.config.enabled:
            return candidates

        for c in candidates:
            # Out-of-Network 且非关注作者的帖子
            if c.source == FeedSource.OUT_NETWORK and not c.is_followed_author:
                # 高互动帖子可以获得加成
                total_engagement = c.num_likes + c.num_shares + c.num_comments
                if total_engagement >= self.config.high_engagement_threshold:
                    c.oon_adjustment = self.config.boost_factor
                    c.final_score *= c.oon_adjustment

        return candidates
