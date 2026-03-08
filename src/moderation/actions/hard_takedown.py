"""
硬性打击动作

封号、删帖（制造"生态位真空"的直接原因）
"""

import logging
from typing import Optional

from ..types import ModerationVerdict, ModerationSeverity, ModerationAction
from ..config import ModerationActionConfig
from ..repository import get_repository


logger = logging.getLogger(__name__)


class HardTakedownAction:
    """
    硬性打击动作

    根据严重程度决定:
    - 删帖: 将帖子状态设为 taken_down
    - 封号: 将用户状态设为 banned

    这是制造"生态位真空"的直接手段
    """

    def __init__(self, config: ModerationActionConfig):
        """
        初始化硬性打击动作

        Args:
            config: 动作配置
        """
        self.config = config
        self.repository = get_repository()

    def execute(self, verdict: ModerationVerdict) -> bool:
        """
        执行硬性打击

        Args:
            verdict: 审核裁决

        Returns:
            是否执行成功
        """
        # 检查是否需要封号
        should_ban = self._should_ban_user(verdict)

        # 检查是否需要删帖
        should_takedown = self._should_takedown_post(verdict)

        if should_ban:
            self._ban_user(verdict)

        if should_takedown:
            self._takedown_post(verdict)

        action_taken = []
        if should_ban:
            action_taken.append("封号")
        if should_takedown:
            action_taken.append("删帖")

        logger.warning(
            f"Hard takedown executed on post {verdict.post_id}, "
            f"user {verdict.user_id}: {', '.join(action_taken)}"
        )

        return True

    def _should_ban_user(self, verdict: ModerationVerdict) -> bool:
        """
        判断是否应该封号

        Args:
            verdict: 审核裁决

        Returns:
            是否封号
        """
        # 检查是否在封号豁免列表中（如新闻发布账号）
        ban_exempt_users = getattr(self.config, 'ban_exempt_users', [])
        if verdict.user_id in ban_exempt_users:
            logger.info(
                f"User {verdict.user_id} is exempt from ban (in ban_exempt_users), "
                f"post will be taken down but account remains active"
            )
            return False

        # 检查封号阈值
        for severity, threshold in self.config.ban_thresholds.items():
            if verdict.severity == severity and verdict.confidence >= threshold:
                return True

        return False

    def _should_takedown_post(self, verdict: ModerationVerdict) -> bool:
        """
        判断是否应该删帖

        Args:
            verdict: 审核裁决

        Returns:
            是否删帖
        """
        # 硬性打击动作意味着至少要删帖
        return True

    def _ban_user(self, verdict: ModerationVerdict):
        """封禁用户"""
        conn = self.repository.conn
        conn.execute('''
            UPDATE users
            SET status = 'banned',
                ban_reason = ?,
                banned_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
        ''', (verdict.reason, verdict.user_id))

        logger.warning(f"User {verdict.user_id} banned: {verdict.reason}")

    def _takedown_post(self, verdict: ModerationVerdict):
        """删除帖子"""
        conn = self.repository.conn
        conn.execute('''
            UPDATE posts
            SET status = 'taken_down',
                takedown_reason = ?,
                takedown_timestamp = CURRENT_TIMESTAMP,
                moderation_action = ?,
                moderation_reason = ?,
                moderated_at = CURRENT_TIMESTAMP
            WHERE post_id = ?
        ''', (
            verdict.reason,
            ModerationAction.HARD_TAKEDOWN.value,
            verdict.reason,
            verdict.post_id,
        ))

        logger.warning(f"Post {verdict.post_id} taken down: {verdict.reason}")

    def check_user_banned(self, user_id: str) -> bool:
        """
        检查用户是否被封禁

        Args:
            user_id: 用户 ID

        Returns:
            是否被封禁
        """
        conn = self.repository.conn
        cursor = conn.cursor()
        cursor.execute('''
            SELECT status FROM users WHERE user_id = ?
        ''', (user_id,))

        row = cursor.fetchone()
        return row and row[0] == 'banned'

    def unban_user(self, user_id: str) -> bool:
        """
        解封用户

        Args:
            user_id: 用户 ID

        Returns:
            是否执行成功
        """
        conn = self.repository.conn
        conn.execute('''
            UPDATE users
            SET status = 'active',
                ban_reason = NULL,
                banned_at = NULL
            WHERE user_id = ?
        ''', (user_id,))

        logger.info(f"User {user_id} unbanned")
        return True

    def restore_post(self, post_id: str) -> bool:
        """
        恢复已删除的帖子

        Args:
            post_id: 帖子 ID

        Returns:
            是否执行成功
        """
        conn = self.repository.conn
        conn.execute('''
            UPDATE posts
            SET status = 'active',
                takedown_reason = NULL,
                takedown_timestamp = NULL,
                moderation_action = NULL,
                moderation_reason = NULL,
                moderated_at = NULL
            WHERE post_id = ?
        ''', (post_id,))

        logger.info(f"Post {post_id} restored")
        return True
