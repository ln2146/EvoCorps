import os
import sys
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(SCRIPT_DIR, 'src')
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from agent_user import build_comment_moderation_feedback


class CommentModerationPolicyTest(unittest.TestCase):
    def test_should_warn_before_ban(self):
        banned, msg = build_comment_moderation_feedback(1, 3)
        self.assertFalse(banned)
        self.assertIn("1/3", msg)

    def test_should_ban_at_threshold(self):
        banned, msg = build_comment_moderation_feedback(3, 3)
        self.assertTrue(banned)
        self.assertIn("已封禁", msg)


if __name__ == "__main__":
    unittest.main()
