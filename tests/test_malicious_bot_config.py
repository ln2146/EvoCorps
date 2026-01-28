import asyncio
import os
import sqlite3
import sys


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)


def test_fake_news_attack_size_uses_config(monkeypatch):
    import malicious_bot_manager as mbm

    class DummyCluster:
        def __init__(self, cluster_size):
            self.cluster_size = cluster_size

    monkeypatch.setattr(mbm, "SimpleMaliciousCluster", DummyCluster)

    conn = sqlite3.connect(":memory:")
    conn.execute(
        """
        CREATE TABLE posts (
            post_id TEXT,
            content TEXT,
            author_id TEXT,
            is_news INTEGER,
            news_type TEXT,
            status TEXT,
            num_comments INTEGER,
            num_likes INTEGER,
            num_shares INTEGER
        )
        """
    )
    conn.execute("CREATE TABLE post_timesteps (post_id TEXT, time_step INTEGER)")
    conn.execute(
        """
        INSERT INTO posts (post_id, content, author_id, is_news, news_type, status, num_comments, num_likes, num_shares)
        VALUES ('post-1', 'fake content', 'user-1', 1, 'fake', 'active', 0, 0, 0)
        """
    )
    conn.execute("INSERT INTO post_timesteps (post_id, time_step) VALUES ('post-1', 1)")
    conn.commit()

    class DummyDB:
        def __init__(self, conn):
            self.conn = conn

    config = {
        "malicious_bot_system": {
            "enabled": True,
            "cluster_size": 9,
            "fake_news_attack_size": 3
        }
    }

    manager = mbm.MaliciousBotManager(config, DummyDB(conn))
    manager.current_time_step = 2

    captured = []

    async def fake_execute(post_id, content, user_id, override_cluster_size=None):
        captured.append(override_cluster_size)
        return {"success": True, "comment_ids": []}

    manager._execute_attack = fake_execute

    asyncio.run(manager.attack_top_hot_posts())

    assert captured == [3]
