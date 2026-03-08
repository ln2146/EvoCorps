import os
import sqlite3
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(SCRIPT_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

import control_flags
from malicious_bots.malicious_bot_manager import MaliciousBotManager


class MaliciousCommentModerationTest(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        cursor = self.conn.cursor()
        cursor.execute(
            """
            CREATE TABLE users (
                user_id TEXT PRIMARY KEY,
                status TEXT DEFAULT 'active',
                comment_violation_count INTEGER DEFAULT 0,
                ban_reason TEXT,
                banned_at TIMESTAMP
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE user_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                action_type TEXT,
                target_id TEXT,
                content TEXT
            )
            """
        )
        self.conn.commit()

        self.manager = object.__new__(MaliciousBotManager)
        self.manager.comment_ban_threshold = 3
        self.manager._ban_exempt_users = set()
        self.manager._comment_keyword_provider = None

    def tearDown(self):
        self.conn.close()

    def _insert_user(self, user_id: str, status: str = "active", violations: int = 0):
        self.conn.execute(
            "INSERT INTO users(user_id, status, comment_violation_count) VALUES (?, ?, ?)",
            (user_id, status, violations),
        )
        self.conn.commit()

    def test_banned_user_should_be_blocked(self):
        self._insert_user("u1", status="banned", violations=5)
        cur = self.conn.cursor()

        with patch.object(control_flags, "moderation_enabled", True):
            blocked = self.manager._check_comment_policy_violation(
                cursor=cur,
                user_id="u1",
                post_id="p1",
                comment_id="c1",
                content="hello",
            )

        self.assertTrue(blocked)

    def test_flagged_comment_should_increment_violation_and_warn(self):
        self._insert_user("u2", status="active", violations=0)
        self.manager._comment_keyword_provider = SimpleNamespace(
            check=lambda content, metadata=None: SimpleNamespace(detected_keywords=["kill"])
        )
        cur = self.conn.cursor()

        with patch.object(control_flags, "moderation_enabled", True):
            blocked = self.manager._check_comment_policy_violation(
                cursor=cur,
                user_id="u2",
                post_id="p1",
                comment_id="c2",
                content="kill",
            )
        self.conn.commit()

        self.assertTrue(blocked)
        row = self.conn.execute(
            "SELECT status, comment_violation_count FROM users WHERE user_id = ?",
            ("u2",),
        ).fetchone()
        self.assertEqual("active", row[0])
        self.assertEqual(1, row[1])
        action_count = self.conn.execute(
            "SELECT COUNT(*) FROM user_actions WHERE user_id = ? AND action_type = 'moderation_warning'",
            ("u2",),
        ).fetchone()[0]
        self.assertEqual(1, action_count)

    def test_third_violation_should_ban_user(self):
        self._insert_user("u3", status="active", violations=2)
        self.manager._comment_keyword_provider = SimpleNamespace(
            check=lambda content, metadata=None: SimpleNamespace(detected_keywords=["nazi"])
        )
        cur = self.conn.cursor()

        with patch.object(control_flags, "moderation_enabled", True):
            blocked = self.manager._check_comment_policy_violation(
                cursor=cur,
                user_id="u3",
                post_id="p1",
                comment_id="c3",
                content="nazi",
            )
        self.conn.commit()

        self.assertTrue(blocked)
        row = self.conn.execute(
            "SELECT status, comment_violation_count, ban_reason FROM users WHERE user_id = ?",
            ("u3",),
        ).fetchone()
        self.assertEqual("banned", row[0])
        self.assertEqual(3, row[1])
        self.assertEqual("comment_keyword_violations", row[2])

    def test_exempt_user_should_skip_comment_policy(self):
        self._insert_user("agentverse_news", status="active", violations=0)
        self.manager._ban_exempt_users = {"agentverse_news"}
        self.manager._comment_keyword_provider = SimpleNamespace(
            check=lambda content, metadata=None: SimpleNamespace(detected_keywords=["kill"])
        )
        cur = self.conn.cursor()

        with patch.object(control_flags, "moderation_enabled", True):
            blocked = self.manager._check_comment_policy_violation(
                cursor=cur,
                user_id="agentverse_news",
                post_id="p1",
                comment_id="c4",
                content="kill",
            )
        self.conn.commit()

        self.assertFalse(blocked)
        row = self.conn.execute(
            "SELECT status, comment_violation_count FROM users WHERE user_id = ?",
            ("agentverse_news",),
        ).fetchone()
        self.assertEqual("active", row[0])
        self.assertEqual(0, row[1])

    def test_moderation_disabled_should_skip_keyword_block(self):
        self._insert_user("u4", status="active", violations=0)
        self.manager._comment_keyword_provider = SimpleNamespace(
            check=lambda content, metadata=None: SimpleNamespace(detected_keywords=["kill"])
        )
        cur = self.conn.cursor()

        with patch.object(control_flags, "moderation_enabled", False):
            blocked = self.manager._check_comment_policy_violation(
                cursor=cur,
                user_id="u4",
                post_id="p1",
                comment_id="c5",
                content="kill",
            )
        self.conn.commit()

        self.assertFalse(blocked)
        row = self.conn.execute(
            "SELECT status, comment_violation_count FROM users WHERE user_id = ?",
            ("u4",),
        ).fetchone()
        self.assertEqual("active", row[0])
        self.assertEqual(0, row[1])


if __name__ == "__main__":
    unittest.main()
