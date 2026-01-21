import argparse
import csv
import os
import sqlite3
from datetime import datetime
from typing import Optional


def clip(text: str, max_len: int = 160) -> str:
    if text is None:
        return ''
    text = str(text).replace('\n', ' ').strip()
    return text if len(text) <= max_len else text[: max_len - 1] + '…'


def ensure_dir(path: str):
    d = os.path.dirname(path)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)


def fetch_top2_news(conn: sqlite3.Connection):
    cur = conn.cursor()
    cur.execute(
        '''
        SELECT post_id
        FROM posts
        WHERE is_news = 1 AND (status IS NULL OR status != 'taken_down')
        ORDER BY (COALESCE(num_comments,0)+COALESCE(num_likes,0)+COALESCE(num_shares,0)) DESC
        LIMIT 2
        '''
    )
    return {row[0] for row in cur.fetchall()}


def export(conn: sqlite3.Connection, step: Optional[int], user: Optional[str], out_path: Optional[str]):
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    params = []
    where = []
    if step is not None:
        where.append('fe.time_step = ?')
        params.append(step)
    if user:
        where.append('fe.user_id = ?')
        params.append(user)
    where_sql = 'WHERE ' + ' AND '.join(where) if where else ''

    # Pre-compute top2 news
    top2 = fetch_top2_news(conn)

    # Query exposures with post info and helper flags
    cur.execute(
        f'''
        SELECT 
            fe.time_step,
            fe.user_id,
            fe.post_id,
            p.author_id,
            p.is_news,
            p.created_at,
            COALESCE(p.num_comments,0)+COALESCE(p.num_likes,0)+COALESCE(p.num_shares,0) AS engagement,
            p.summary,
            p.content,
            EXISTS(
                SELECT 1 FROM post_timesteps pt 
                WHERE pt.post_id = p.post_id AND pt.time_step = fe.time_step
            ) AS is_current_step_news,
            CASE WHEN p.post_id IN ({','.join(['?']*len(top2)) if top2 else 'SELECT p2.post_id FROM posts p2 WHERE 1=0'}) THEN 1 ELSE 0 END AS is_top2_hot,
            EXISTS(
                SELECT 1 FROM follows f 
                WHERE f.follower_id = fe.user_id AND f.followed_id = p.author_id
            ) AS is_followed_author
        FROM feed_exposures fe
        JOIN posts p ON p.post_id = fe.post_id
        {where_sql}
        ORDER BY fe.time_step ASC, fe.user_id ASC, p.is_news DESC, engagement DESC
        ''',
        params + (list(top2) if top2 else []),
    )

    rows = cur.fetchall()

    headers = [
        'time_step', 'user_id', 'post_id', 'is_news', 'engagement', 'author_id', 'created_at',
        'is_top2_hot', 'is_current_step_news', 'is_mid_engagement_news', 'is_followed_author',
        'summary_or_content'
    ]

    if out_path:
        ensure_dir(out_path)
        out_f = open(out_path, 'w', newline='', encoding='utf-8')
        writer = csv.writer(out_f)
        writer.writerow(headers)
    else:
        writer = csv.writer(os.sys.stdout)

    for r in rows:
        engagement = int(r['engagement'] or 0)
        is_mid = 1 if (3 <= engagement <= 10 and int(r['is_news']) == 1) else 0
        writer.writerow([
            r['time_step'],
            r['user_id'],
            r['post_id'],
            int(r['is_news'] or 0),
            engagement,
            r['author_id'],
            r['created_at'],
            int(r['is_top2_hot'] or 0),
            int(r['is_current_step_news'] or 0),
            is_mid,
            int(r['is_followed_author'] or 0),
            clip(r['summary'] or r['content']),
        ])

    if out_path:
        out_f.close()


def parse_args():
    ap = argparse.ArgumentParser(description='Export per-step per-user read posts (feed exposures) with content.')
    ap.add_argument('--step', type=int, default=None, help='Specific time_step to export (default: all)')
    ap.add_argument('--user', type=str, default=None, help='Specific user_id to export (default: all)')
    ap.add_argument('--out', type=str, default=None, help='Output CSV path (default: print to stdout)')
    return ap.parse_args()


def main():
    args = parse_args()
    db_path = os.path.join('database', 'simulation.db')
    conn = sqlite3.connect(db_path)
    try:
        if not args.out:
            export(conn, args.step, args.user, None)
        else:
            out_path = args.out
            if out_path.endswith('/') or out_path.endswith('\\'):
                ts = datetime.now().strftime('%Y%m%d_%H%M%S')
                fname = f'read_posts_{ts}.csv'
                out_path = os.path.join(out_path, fname)
            export(conn, args.step, args.user, out_path)
            print(f'Exported to: {out_path}')
    finally:
        conn.close()


if __name__ == '__main__':
    main()
