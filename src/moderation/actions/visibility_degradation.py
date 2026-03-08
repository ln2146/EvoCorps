"""
可见性降级动作

在推荐系统中降低内容的权重，但不完全删除
"""

import logging
from typing import Optional

from ..types import ModerationVerdict, ModerationSeverity
from ..config import ModerationActionConfig
from ..repository import get_repository


logger = logging.getLogger(__name__)


class VisibilityDegradationAction:
    """
    可见性降级动作

    不删帖，但在推荐算法中强制降低特定标签或词汇的权重
    这是实现"生态位真空"的主要手段之一
    """

    def __init__(self, config: ModerationActionConfig):
        """
        初始化可见性降级动作

        Args:
            config: 动作配置
        """
        self.config = config
        self.repository = get_repository()

    def execute(self, verdict: ModerationVerdict) -> bool:
        """
        执行可见性降级

        Args:
            verdict: 审核裁决

        Returns:
            是否执行成功
        """
        # 获取降级系数
        factor = self.config.visibility_degradation_factors.get(
            verdict.severity,
            0.5  # 默认降低 50%
        )

        # 更新裁决的降级系数
        verdict.degradation_factor = factor

        # 更新数据库
        self.repository.update_post_moderation(
            post_id=verdict.post_id,
            action="visibility_degradation",
            degradation_factor=factor,
            reason=verdict.reason,
        )

        logger.info(
            f"Visibility degradation applied to post {verdict.post_id}: "
            f"factor={factor}, severity={verdict.severity}"
        )

        return True

    def get_factor(self, severity: ModerationSeverity) -> float:
        """
        获取指定严重程度的降级系数

        Args:
            severity: 严重程度

        Returns:
            降级系数 (0.0 - 1.0)
        """
        return self.config.visibility_degradation_factors.get(
            severity,
            0.5
        )

    def revert(self, post_id: str) -> bool:
        """
        撤销降级，恢复正常可见性

        Args:
            post_id: 帖子 ID

        Returns:
            是否执行成功
        """
        self.repository.update_post_moderation(
            post_id=post_id,
            action="none",
            degradation_factor=1.0,
            reason="降级已撤销",
        )

        logger.info(f"Visibility degradation reverted for post {post_id}")
        return True
