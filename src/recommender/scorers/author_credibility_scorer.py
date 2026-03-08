"""
作者信誉评分器

阶段5.35: 根据 users.influence_score 调整候选帖子的 final_score，
区分高信誉作者（加成）与疑似水军账号（惩罚）。
"""

from typing import List
from ..types import PostCandidate
from ..config import AuthorCredibilityConfig


class AuthorCredibilityScorer:
    """
    作者信誉评分器

    评分公式（分段线性映射 influence_score → 调整因子）:
        influence >= high_threshold  →  factor = high_credibility_boost
        influence <= low_threshold   →  factor = low_credibility_penalty
        中间区间                     →  线性插值（平滑过渡）

    最终: final_score *= clamp(factor, min_penalty_factor, max_boost_factor)
    """

    def __init__(self, config: AuthorCredibilityConfig):
        self.config = config

    def score(self, candidates: List[PostCandidate]) -> List[PostCandidate]:
        """
        应用作者信誉调整

        Args:
            candidates: 候选帖子列表（已由 WeightedScorer/OONScorer 计算 weighted_score）

        Returns:
            调整后的候选帖子列表
        """
        if not self.config.enabled:
            return candidates

        cfg = self.config
        for candidate in candidates:
            influence = candidate.author_influence_score
            if influence is None:
                influence = cfg.default_influence_score

            factor = self._compute_factor(influence, cfg)
            factor = max(cfg.min_penalty_factor, min(cfg.max_boost_factor, factor))

            candidate.final_score *= factor

        return candidates

    @staticmethod
    def _compute_factor(influence: float, cfg: AuthorCredibilityConfig) -> float:
        """分段线性映射 influence_score → 调整因子"""
        if influence >= cfg.high_credibility_threshold:
            return cfg.high_credibility_boost
        if influence <= cfg.low_credibility_threshold:
            return cfg.low_credibility_penalty
        # 线性插值：[low_threshold, high_threshold] → [penalty, boost]
        ratio = (influence - cfg.low_credibility_threshold) / (
            cfg.high_credibility_threshold - cfg.low_credibility_threshold
        )
        return cfg.low_credibility_penalty + ratio * (
            cfg.high_credibility_boost - cfg.low_credibility_penalty
        )
