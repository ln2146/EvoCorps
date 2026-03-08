"""
警告标签动作

给违规内容打上官方标签
"""

import logging
from typing import Optional

from ..types import ModerationVerdict, ModerationCategory
from ..config import ModerationActionConfig
from ..repository import get_repository


logger = logging.getLogger(__name__)


class WarningLabelAction:
    """
    警告标签动作

    不删帖，但给内容打上官方警告标签
    让用户知晓内容可能存在问题
    """

    def __init__(self, config: ModerationActionConfig):
        """
        初始化警告标签动作

        Args:
            config: 动作配置
        """
        self.config = config
        self.repository = get_repository()

    def execute(self, verdict: ModerationVerdict) -> bool:
        """
        执行警告标签

        Args:
            verdict: 审核裁决

        Returns:
            是否执行成功
        """
        # 获取标签文字
        label_text = self._get_label_text(verdict)

        # 更新裁决的标签文字
        verdict.label_text = label_text

        # 更新数据库
        self.repository.update_post_moderation(
            post_id=verdict.post_id,
            action="warning_label",
            label_text=label_text,
            reason=verdict.reason,
        )

        logger.info(
            f"Warning label applied to post {verdict.post_id}: "
            f"label='{label_text}', category={verdict.category}"
        )

        return True

    def _get_label_text(self, verdict: ModerationVerdict) -> str:
        """
        获取标签文字

        Args:
            verdict: 审核裁决

        Returns:
            标签文字
        """
        # 优先使用配置中该分类的标签
        if verdict.category in self.config.warning_labels:
            return self.config.warning_labels[verdict.category]

        # 尝试使用枚举匹配
        for category_key, label in self.config.warning_labels.items():
            try:
                if ModerationCategory(category_key) == verdict.category:
                    return label
            except ValueError:
                pass

        # 默认标签
        return self.config.warning_labels.get("other", "⚠️ 此内容需谨慎参考")

    def get_label(self, category: ModerationCategory) -> str:
        """
        获取指定分类的标签文字

        Args:
            category: 内容分类

        Returns:
            标签文字
        """
        if category.value in self.config.warning_labels:
            return self.config.warning_labels[category.value]

        for category_key, label in self.config.warning_labels.items():
            try:
                if ModerationCategory(category_key) == category:
                    return label
            except ValueError:
                pass

        return "⚠️ 此内容需谨慎参考"

    def revert(self, post_id: str) -> bool:
        """
        撤销警告标签

        Args:
            post_id: 帖子 ID

        Returns:
            是否执行成功
        """
        self.repository.update_post_moderation(
            post_id=post_id,
            action="none",
            label_text=None,
            reason="警告已撤销",
        )

        logger.info(f"Warning label reverted for post {post_id}")
        return True
