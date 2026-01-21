import sqlite3
import re
import sys

DB_PATH = 'database/simulation.db'
LOG_PATH = 'temp_reaction_log.jsonl'


def get_comment_count(post_id: str) -> int:
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute('SELECT COALESCE(num_comments,0) FROM posts WHERE post_id=?', (post_id,))
        row = cur.fetchone()
        conn.close()
        return int(row[0]) if row else 0
    except Exception:
        return -1


def count_in_prompts(post_id: str) -> int:
    """Count how many prompts included this post.
    Each log line typically lists posts twice (once in 'prompt', once in 'feed_content').
    We count raw occurrences and divide by 2 to estimate prompt instances.
    """
    try:
        with open(LOG_PATH, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        return 0
    raw = len(re.findall(rf"post_id:\s*{re.escape(post_id)}\b", content))
    return raw // 2 if raw else 0


def main(ids):
    for pid in ids:
        comments = get_comment_count(pid)
        in_prompts = count_in_prompts(pid)
        print(f"{pid}: comments={comments}, prompts={in_prompts}")


if __name__ == '__main__':
    ids = sys.argv[1:] or []
    if not ids:
        print('Usage: py -3.9 scripts/post_prompt_stats.py <post_id> [<post_id> ...]')
        sys.exit(1)
    main(ids)

