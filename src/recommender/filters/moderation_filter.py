"""
审核过滤集成

将审核系统与推荐系统连接
"""

import logging
import sys
import os
from typing import List, Optional

# Add src to path for importing control_flags and database_manager
_src_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)

# Use try/except for imports to handle different execution contexts
try:
    from ...moderation.types import ModerationSeverity, ModerationFilterConfig
except (ImportError, ValueError):
    # Fall back to absolute import
    from moderation.types import ModerationSeverity, ModerationFilterConfig

from ..types import PostCandidate
from database.database_manager import fetch_one, fetch_all


logger = logging.getLogger(__name__)


class ModerationFilter:
    """
    审核过滤集成

    在推荐系统中应用审核结果:
    1. 过滤掉已被硬删的帖子
    2. 应用可见性降级（降低推荐权重）
    3. 保留警告标签（用于前端显示）
    """

    def __init__(self, config: ModerationFilterConfig = None):
        """
        初始化审核过滤

        Args:
            config: 过滤配置
        """
        self.config = config or ModerationFilterConfig()

    def filter(
        self,
        candidates: List[PostCandidate],
        apply_degradation: bool = None
    ) -> List[PostCandidate]:
        """
        应用审核过滤

        Args:
            candidates: 候选帖子列表
            apply_degradation: 是否应用降级，None 时使用配置

        Returns:
            过滤后的候选列表

        Raises:
            RuntimeError: If moderation is disabled via control_flags
        """
        # Import control_flags here to avoid circular import
        import control_flags

        # NO FALLBACK: Require moderation to be enabled via control_flags
        if not control_flags.moderation_enabled:
            raise RuntimeError(
                "ModerationFilter.filter() called but control_flags.moderation_enabled is False. "
                "Enable moderation via the control API or set control_flags.moderation_enabled = True"
            )

        apply_degradation = (
            apply_degradation
            if apply_degradation is not None
            else self.config.apply_degradation
        )

        # 批量查询被删帖（单次 DB 请求，避免循环内 N 次查询）
        taken_down_ids: set = set()
        if self.config.filter_taken_down and candidates:
            post_ids = tuple(str(c.post_id) for c in candidates)
            placeholders = ','.join('?' * len(post_ids))
            rows = fetch_all(
                f'SELECT post_id FROM posts WHERE post_id IN ({placeholders}) AND status = "taken_down"',
                post_ids
            )
            taken_down_ids = {str(row['post_id']) for row in rows}

        filtered = []
        removed_count = 0
        degraded_count = 0

        for candidate in candidates:
            # 1. 过滤已删帖（实时 DB 状态，非快照字段）
            if self.config.filter_taken_down and str(candidate.post_id) in taken_down_ids:
                removed_count += 1
                continue

            # 2. 应用可见性降级
            if apply_degradation:
                degraded = self._apply_degradation(candidate)
                if degraded:
                    degraded_count += 1

            # 3. 应用封号用户过滤
            if self._is_user_banned(candidate):
                removed_count += 1
                continue

            filtered.append(candidate)

        if removed_count > 0 or degraded_count > 0:
            logger.debug(
                f"Moderation filter: removed={removed_count}, "
                f"degraded={degraded_count}, remaining={len(filtered)}"
            )

        return filtered

    def _apply_degradation(self, candidate: PostCandidate) -> bool:
        """
        应用可见性降级

        Args:
            candidate: 候选帖子

        Returns:
            是否应用了降级
        """
        # Use the moderation_degradation_factor field directly
        degradation_factor = candidate.moderation_degradation_factor

        if degradation_factor < 1.0:
            # 降低最终分数
            candidate.final_score *= degradation_factor
            return True

        return False

    def _is_user_banned(self, candidate: PostCandidate) -> bool:
        """
        检查用户是否被封禁

        Args:
            candidate: 候选帖子

        Returns:
            用户是否被封禁
        """
        user = fetch_one(
            'SELECT status FROM users WHERE user_id = ?',
            (candidate.author_id,)
        )
        if user and user.get('status') == 'banned':
            return True

        return False

    def get_warning_label(self, post_id: str) -> Optional[str]:
        """
        获取帖子的警告标签

        Args:
            post_id: 帖子 ID

        Returns:
            警告标签文字，如果没有则返回 None
        """
        post = fetch_one(
            'SELECT moderation_label FROM posts WHERE post_id = ?',
            (post_id,)
        )
        if post:
            return post.get('moderation_label')

        return None

    def get_degradation_factor(self, severity: ModerationSeverity) -> float:
        """
        获取指定严重程度的降级系数

        Args:
            severity: 严重程度

        Returns:
            降级系数
        """
        return self.config.visibility_factors.get(severity, 1.0)

    def set_config(self, config: ModerationFilterConfig):
        """
        更新配置

        Args:
            config: 新配置
        """
        self.config = config
