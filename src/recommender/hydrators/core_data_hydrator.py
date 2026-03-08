"""
核心数据水合器

阶段3: 计算帖子年龄等核心数据
"""

from typing import List, Dict
from ..types import PostCandidate


class CoreDataHydrator:
    """
    核心数据水合器

    计算帖子的 age_steps 等核心数据
    """

    def hydrate(
        self,
        candidates: List[PostCandidate],
        post_timesteps: Dict[str, int],
        current_step: int
    ) -> List[PostCandidate]:
        """
        水合核心数据

        Args:
            candidates: 候选帖子列表
            post_timesteps: {post_id: time_step} 映射
            current_step: 当前时间步

        Returns:
            填充了 age_steps 的候选帖子列表
        """
        for candidate in candidates:
            pstep = post_timesteps.get(candidate.post_id)
            if pstep is not None:
                candidate.age_steps = max(0, current_step - pstep)
            else:
                candidate.age_steps = 0

        return candidates
