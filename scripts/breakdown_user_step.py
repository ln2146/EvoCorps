import sqlite3
import sys

def main(user_id: str, step: int):
    conn = sqlite3.connect('database/simulation.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute('''
        SELECT fe.post_id, p.is_news,
               COALESCE(p.num_comments,0)+COALESCE(p.num_likes,0)+COALESCE(p.num_shares,0) AS engagement,
               EXISTS(SELECT 1 FROM post_timesteps pt WHERE pt.post_id = p.post_id AND pt.time_step = fe.time_step) AS is_current_step
        FROM feed_exposures fe
        JOIN posts p ON p.post_id = fe.post_id
        WHERE fe.user_id = ? AND fe.time_step = ?
    ''', (user_id, step))
    rows = [dict(r) for r in cur.fetchall()]
    print('total:', len(rows))
    print('news:', sum(1 for r in rows if r['is_news']))
    print('current_step_news:', sum(1 for r in rows if r['is_news'] and r['is_current_step']))
    print('mid_engagement_news:', sum(1 for r in rows if r['is_news'] and 3 <= r['engagement'] <= 10))
    conn.close()

if __name__ == '__main__':
    user = sys.argv[1] if len(sys.argv) > 1 else 'user-32daa1'
    step = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    main(user, step)

