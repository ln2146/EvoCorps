"""
后选择过滤器

阶段7: 在选择后进行最终清理
"""

from typing import List
from ..types import PostCandidate


class PostSelectionFilters:
    """
    后选择过滤器

    在 Top-K 选择后进行最终清理
    """

    def filter(self, candidates: List[PostCandidate]) -> List[PostCandidate]:
        """
        应用所有后选择过滤器

        Args:
            candidates: 候选帖子列表

        Returns:
            过滤后的候选帖子列表
        """
        filtered = candidates

        # 1. 最终去重 (确保没有重复)
        filtered = self._final_dedup(filtered)

        # 2. 状态检查 (确保没有被删除的帖子)
        filtered = self._check_status(filtered)

        return filtered

    def _final_dedup(self, candidates: List[PostCandidate]) -> List[PostCandidate]:
        """最终去重"""
        seen = set()
        unique = []
        for c in candidates:
            if c.post_id not in seen:
                seen.add(c.post_id)
                unique.append(c)
        return unique

    def _check_status(self, candidates: List[PostCandidate]) -> List[PostCandidate]:
        """检查帖子状态"""
        return [c for c in candidates if c.status != 'taken_down']
