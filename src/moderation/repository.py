"""
审核记录存储

遵循 AGENT_ENVIRONMENT_SPEC.md: Repo 层负责数据持久化
"""

import json
import logging
import sqlite3
import os
from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import asdict

from .types import ModerationVerdict, ModerationStats, ModerationAction, ModerationSeverity, ModerationCategory


logger = logging.getLogger(__name__)


class ModerationRepository:
    """
    审核记录仓储

    负责:
    1. 初始化审核相关数据库表
    2. 保存审核记录
    3. 查询审核历史
    4. 统计审核数据
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        初始化仓储

        Args:
            db_path: 数据库路径，None 时使用默认路径
        """
        self.db_path = self._resolve_db_path(db_path)
        self.conn = None
        self._connect()

    def _resolve_db_path(self, db_path: Optional[str]) -> str:
        """解析数据库路径"""
        if db_path:
            return db_path

        # 尝试多个可能的路径
        possible_paths = [
            "database/simulation.db",
            os.path.join("database", "simulation.db"),
            os.path.join(os.getcwd(), "database", "simulation.db"),
            os.path.join(os.path.dirname(__file__), "..", "database", "simulation.db"),
        ]

        for path in possible_paths:
            if os.path.exists(path):
                return os.path.abspath(path)

        # 默认路径
        return "database/simulation.db"

    def _connect(self):
        """建立数据库连接"""
        try:
            self.conn = sqlite3.connect(
                self.db_path,
                timeout=30.0,
                isolation_level=None  # Autocommit mode
            )
            self.conn.row_factory = sqlite3.Row
            self.conn.execute('PRAGMA journal_mode=WAL')
            self.cursor = self.conn.cursor()

            # 初始化表结构
            self._init_tables()

            logger.info(f"ModerationRepository connected to: {self.db_path}")

        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    def _init_tables(self):
        """初始化审核相关表"""
        # 1. 审核记录表
        try:
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS moderation_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    post_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    category TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    reason TEXT NOT NULL,
                    detected_keywords TEXT,
                    provider TEXT NOT NULL,
                    action TEXT,
                    appealable INTEGER DEFAULT 1,
                    degradation_factor REAL,
                    label_text TEXT,
                    metadata TEXT,
                    checked_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (post_id) REFERENCES posts(post_id),
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')

            # 创建索引
            self.cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_moderation_post_id
                ON moderation_records(post_id)
            ''')
            self.cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_moderation_user_id
                ON moderation_records(user_id)
            ''')
            self.cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_moderation_checked_at
                ON moderation_records(checked_at)
            ''')

        except sqlite3.Error as e:
            logger.error(f"Error creating moderation_records table: {e}")
            raise

        # 2. 为 posts 表添加审核相关字段
        self._add_posts_columns()

    def _add_posts_columns(self):
        """为 posts 表添加审核相关字段"""
        columns = [
            ("moderation_degradation_factor", "REAL DEFAULT 1.0"),
            ("moderation_label", "TEXT"),
            ("moderation_action", "TEXT"),
            ("moderation_reason", "TEXT"),
            ("moderated_at", "TIMESTAMP"),
        ]

        for column_name, column_type in columns:
            try:
                self.cursor.execute(f'''
                    ALTER TABLE posts ADD COLUMN {column_name} {column_type}
                ''')
                logger.info(f"Added column posts.{column_name}")
            except sqlite3.OperationalError:
                pass  # 列已存在

    def save(self, verdict: ModerationVerdict) -> int:
        """
        保存审核记录

        Returns:
            记录 ID
        """
        try:
            keywords_json = json.dumps(verdict.detected_keywords, ensure_ascii=False)
            metadata_json = json.dumps(verdict.metadata, ensure_ascii=False)

            self.cursor.execute('''
                INSERT INTO moderation_records (
                    post_id, user_id, content, category, severity,
                    confidence, reason, detected_keywords, provider,
                    action, appealable, degradation_factor, label_text,
                    metadata, checked_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                verdict.post_id,
                verdict.user_id,
                verdict.content,
                verdict.category,
                verdict.severity,
                verdict.confidence,
                verdict.reason,
                keywords_json,
                verdict.provider,
                verdict.action if verdict.action else None,
                1 if verdict.appealable else 0,
                verdict.degradation_factor,
                verdict.label_text,
                metadata_json,
                verdict.checked_at,
            ))

            record_id = self.cursor.lastrowid
            logger.debug(f"Saved moderation record {record_id} for post {verdict.post_id}")
            return record_id

        except sqlite3.Error as e:
            logger.error(f"Error saving moderation record: {e}")
            raise

    def get_by_post_id(self, post_id: str) -> List[ModerationVerdict]:
        """获取帖子的所有审核记录"""
        self.cursor.execute('''
            SELECT * FROM moderation_records
            WHERE post_id = ?
            ORDER BY checked_at DESC
        ''', (post_id,))

        rows = self.cursor.fetchall()
        return [self._row_to_verdict(row) for row in rows]

    def get_by_user_id(self, user_id: str, limit: int = 100) -> List[ModerationVerdict]:
        """获取用户的审核记录"""
        self.cursor.execute('''
            SELECT * FROM moderation_records
            WHERE user_id = ?
            ORDER BY checked_at DESC
            LIMIT ?
        ''', (user_id, limit))

        rows = self.cursor.fetchall()
        return [self._row_to_verdict(row) for row in rows]

    def get_stats(self, limit: int = 1000) -> ModerationStats:
        """获取审核统计"""
        self.cursor.execute('''
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN action IS NOT NULL AND action != 'none' THEN 1 ELSE 0 END) as flagged
            FROM moderation_records
            LIMIT ?
        ''', (limit,))

        row = self.cursor.fetchone()
        stats = ModerationStats(
            total_checked=row[0] or 0,
            total_flagged=row[1] or 0,
        )

        # 按动作统计
        self.cursor.execute('''
            SELECT action, COUNT(*) as count
            FROM moderation_records
            WHERE action IS NOT NULL
            GROUP BY action
        ''')
        for action_str, count in self.cursor.fetchall():
            try:
                action = ModerationAction(action_str)
                stats.action_counts[action] = count
            except ValueError:
                pass

        # 按严重程度统计
        self.cursor.execute('''
            SELECT severity, COUNT(*) as count
            FROM moderation_records
            GROUP BY severity
        ''')
        for severity_str, count in self.cursor.fetchall():
            try:
                severity = ModerationSeverity(severity_str)
                stats.severity_counts[severity] = count
            except ValueError:
                pass

        # 按分类统计
        self.cursor.execute('''
            SELECT category, COUNT(*) as count
            FROM moderation_records
            GROUP BY category
        ''')
        for category_str, count in self.cursor.fetchall():
            try:
                category = ModerationCategory(category_str)
                stats.category_counts[category] = count
            except ValueError:
                pass

        return stats

    def _row_to_verdict(self, row: sqlite3.Row) -> ModerationVerdict:
        """将数据库行转换为 ModerationVerdict"""
        data = dict(row)

        return ModerationVerdict(
            post_id=data['post_id'],
            user_id=data['user_id'],
            content=data['content'],
            category=ModerationCategory(data['category']),
            severity=ModerationSeverity(data['severity']),
            confidence=data['confidence'],
            reason=data['reason'],
            detected_keywords=json.loads(data['detected_keywords']) if data.get('detected_keywords') else [],
            provider=data['provider'],
            checked_at=datetime.fromisoformat(data['checked_at']),
            metadata=json.loads(data['metadata']) if data.get('metadata') else {},
            action=ModerationAction(data['action']) if data.get('action') else None,
            appealable=bool(data.get('appealable', 1)),
            degradation_factor=data.get('degradation_factor'),
            label_text=data.get('label_text'),
            record_id=data['id'],
        )

    def update_post_moderation(self, post_id: str, action: str, **kwargs):
        """更新帖子的审核状态"""
        updates = ["moderation_action = ?", "moderated_at = CURRENT_TIMESTAMP"]
        values = [action]

        if 'degradation_factor' in kwargs:
            updates.append("moderation_degradation_factor = ?")
            values.append(kwargs['degradation_factor'])

        if 'label_text' in kwargs:
            updates.append("moderation_label = ?")
            values.append(kwargs['label_text'])

        if 'reason' in kwargs:
            updates.append("moderation_reason = ?")
            values.append(kwargs['reason'])

        values.append(post_id)

        query = f"UPDATE posts SET {', '.join(updates)} WHERE post_id = ?"
        self.cursor.execute(query, values)
        logger.debug(f"Updated post {post_id} moderation: action={action}")

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            self.conn = None

    def __del__(self):
        """析构时关闭连接"""
        self.close()


# 单例实例
_repository_instance: Optional[ModerationRepository] = None


def get_repository() -> ModerationRepository:
    """获取审核仓储单例"""
    global _repository_instance
    if _repository_instance is None:
        _repository_instance = ModerationRepository()
    return _repository_instance
