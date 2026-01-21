import sqlite3
from collections import defaultdict
import csv
import json
from pathlib import Path

DB_PATH = 'database/simulation.db'
OUTPUT_CSV = 'logs/comments_num/comments_stats_per_timestep.csv'


def detect_has_agent_type(conn: sqlite3.Connection) -> bool:
    cur = conn.cursor()
    cur.execute('PRAGMA table_info(comments)')
    cols = [r[1] for r in cur.fetchall()]
    return 'agent_type' in cols


def build_exposure_map(conn: sqlite3.Connection):
    """Map (user_id, post_id) -> earliest exposure timestep."""
    cur = conn.cursor()
    cur.execute('SELECT user_id, post_id, MIN(time_step) as step FROM feed_exposures GROUP BY user_id, post_id')
    expo = {}
    for user_id, post_id, step in cur.fetchall():
        expo[(user_id, post_id)] = step
    return expo


def get_post_step(conn: sqlite3.Connection, post_id: str):
    cur = conn.cursor()
    cur.execute('SELECT time_step FROM post_timesteps WHERE post_id = ?', (post_id,))
    row = cur.fetchone()
    return row[0] if row else None


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    expo_map = build_exposure_map(conn)
    has_agent_type = detect_has_agent_type(conn)

    # Prefer precise per-comment timestep if available
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='comment_timesteps'")
    has_comment_timesteps = cur.fetchone() is not None

    # Malicious comment ids (if table exists)
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='malicious_comments'")
    has_malicious_table = cur.fetchone() is not None
    malicious_comment_ids = set()
    if has_malicious_table:
        try:
            cur.execute('SELECT comment_id FROM malicious_comments WHERE comment_id IS NOT NULL')
            malicious_comment_ids = {r[0] for r in cur.fetchall()}
        except Exception:
            malicious_comment_ids = set()

    # Load all comments and JOIN per-comment timesteps correctly
    if has_agent_type:
        select_fields = "c.comment_id, c.author_id, c.post_id, COALESCE(c.agent_type,'normal') AS agent_type"
    else:
        select_fields = "c.comment_id, c.author_id, c.post_id, 'unknown' AS agent_type"

    from_clause = " FROM comments c"
    if has_comment_timesteps:
        select_fields += ", ct.time_step AS exact_step"
        from_clause += " JOIN comment_timesteps ct ON ct.comment_id = c.comment_id"
    else:
        select_fields += ", NULL AS exact_step"

    base_query = f"SELECT {select_fields}{from_clause}"
    cur.execute(base_query)
    comments = cur.fetchall()

    # Totals across all types
    step_total_comments = defaultdict(int)
    step_users = defaultdict(set)

    # Split by category: normal, malicious, echo
    categories = ['normal', 'malicious', 'echo']
    step_total_comments_by_type = {c: defaultdict(int) for c in categories}
    step_users_by_type = {c: defaultdict(set) for c in categories}
    categories_present = set()

    for r in comments:
        uid = r['author_id']
        pid = r['post_id']
        cid = r['comment_id']
        # Determine timestep: prefer exact per-comment step
        step = r['exact_step'] if 'exact_step' in r.keys() else None
        if step is None:
            step = expo_map.get((uid, pid))
        if step is None:
            step = get_post_step(conn, pid)
        if step is None:
            # Unable to attribute to a timestep; skip
            continue
        step_total_comments[step] += 1
        step_users[step].add(uid)

        # Determine category: echo > malicious > normal
        agent_type = (r['agent_type'] or '').lower()
        author_id = (uid or '')
        if 'echo_' in author_id:
            bucket = 'echo'
        elif (agent_type == 'malicious') or (cid in malicious_comment_ids) or ('malicious' in author_id):
            bucket = 'malicious'
        else:
            bucket = 'normal'
        categories_present.add(bucket)
        step_total_comments_by_type[bucket][step] += 1
        step_users_by_type[bucket][step].add(uid)

    # Build rows per timestep
    steps = sorted(set(step_total_comments.keys()) | set(step_users.keys()))
    rows = []
    for s in steps:
        total_comments = step_total_comments.get(s, 0)
        unique_users = len(step_users.get(s, set()))
        avg_per_user = (total_comments / unique_users) if unique_users > 0 else 0.0

        row = {
            'time_step': s,
            'display_step': s + 1,
            'unique_comment_users_total': unique_users,
            'total_comments_total': total_comments,
            'avg_comments_per_user_total': round(avg_per_user, 3),
        }

        # Add only present categories
        for cat in sorted(categories_present):
            c_comments = step_total_comments_by_type[cat].get(s, 0)
            c_users = len(step_users_by_type[cat].get(s, set()))
            row[f'unique_comment_users_{cat}'] = c_users
            row[f'total_comments_{cat}'] = c_comments
            row[f'avg_comments_per_user_{cat}'] = round((c_comments / c_users) if c_users > 0 else 0.0, 3)

        rows.append(row)

    # Ensure parent directory exists
    out_path = Path(OUTPUT_CSV)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Write CSV with fixed Chinese headers and order
    headers = [
        '时间步',
        '当前时间步下评论总用户数',
        '当前时间步下评论总数',
        '当前时间步下评论普通用户数',
        '当前时间步下普通用户评论总数',
        '当前时间步下评论恶意用户数',
        '当前时间步下恶意用户评论总数',
        '当前时间步下评论附和用户数',
        '当前时间步下附和用户评论总数',
    ]

    def to_row_dict(r: dict) -> dict:
        n_users = r.get('unique_comment_users_normal', 0)
        m_users = r.get('unique_comment_users_malicious', 0)
        e_users = r.get('unique_comment_users_echo', 0)
        n_comments = r.get('total_comments_normal', 0)
        m_comments = r.get('total_comments_malicious', 0)
        e_comments = r.get('total_comments_echo', 0)
        return {
            '时间步': r['display_step'],
            '当前时间步下评论总用户数': r.get('unique_comment_users_total', 0),
            '当前时间步下评论总数': r.get('total_comments_total', 0),
            '当前时间步下评论普通用户数': n_users,
            '当前时间步下普通用户评论总数': n_comments,
            '当前时间步下评论恶意用户数': m_users,
            '当前时间步下恶意用户评论总数': m_comments,
            '当前时间步下评论附和用户数': e_users,
            '当前时间步下附和用户评论总数': e_comments,
        }

    with out_path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for r in rows:
            writer.writerow(to_row_dict(r))

    print(json.dumps({'rows': rows, 'csv': str(out_path), 'categories_present': sorted(categories_present)}, ensure_ascii=False))

    conn.close()


if __name__ == '__main__':
    main()
