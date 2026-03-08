"""
加权评分器

阶段5: 基于互动数据计算加权分数
对齐 Notice.md: Score = w1*Likes + w2*Shares*2 + w3*Comments
"""

from typing import List
from ..types import PostCandidate
from ..config import ScoringWeights, FreshnessConfig


class WeightedScorer:
    """
    加权评分器

    对齐 Notice.md 的评分公式:
    Score = w1*Likes + w2*Shares*2 + w3*Comments

    水军攻击的就是这个权重公式，通过短时间内集中点赞和转发，
    强行拉高假新闻的 Score，进而操纵 Out-Network 召回
    """

    def __init__(self, weights: ScoringWeights):
        self.weights = weights

    def score(
        self,
        candidates: List[PostCandidate],
        freshness_config: FreshnessConfig
    ) -> List[PostCandidate]:
        """
        计算加权分数

        Args:
            candidates: 候选帖子列表
            freshness_config: 新鲜度配置

        Returns:
            填充了评分字段的候选帖子列表
        """
        for c in candidates:
            # 互动加权评分: Score = w1*Likes + w2*Shares*2 + w3*Comments
            # 注意: w_shares 已经是 2.0，所以这里不需要再乘 2
            engagement = (
                self.weights.w_likes * c.num_likes +
                self.weights.w_shares * c.num_shares +
                self.weights.w_comments * c.num_comments
            )
            c.engagement_score = engagement

            # 新鲜度衰减: freshness = max(min_freshness, 1.0 - decay_rate × age)
            freshness = max(
                freshness_config.min_freshness,
                1.0 - freshness_config.decay_rate * c.age_steps
            )
            c.freshness_score = freshness

            # 加权分数 = (engagement + bias) × freshness
            c.weighted_score = (engagement + freshness_config.bias) * freshness

            # 初始化最终分数
            c.final_score = c.weighted_score

        return candidates
