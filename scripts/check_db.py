import sqlite3
import os

def main():
    db_path = os.path.join('database', 'simulation.db')
    print('DB exists:', os.path.exists(db_path))
    if not os.path.exists(db_path):
        return
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r['name'] for r in cur.fetchall()]
    print('Tables:', tables)

    if 'post_timesteps' in tables:
        cur.execute('SELECT COUNT(*) AS c FROM post_timesteps')
        print('post_timesteps count:', cur.fetchone()['c'])
        cur.execute('SELECT time_step, COUNT(*) c FROM post_timesteps GROUP BY time_step ORDER BY time_step DESC LIMIT 5')
        print('recent post_timesteps by step:', [dict(r) for r in cur.fetchall()])

    if 'feed_exposures' in tables:
        cur.execute('SELECT MAX(time_step) AS m FROM feed_exposures')
        row = cur.fetchone()
        max_step = row['m']
        print('max exposure step:', max_step)
        if max_step is not None:
            step = max_step
            cur.execute('SELECT user_id, COUNT(*) c FROM feed_exposures WHERE time_step=? GROUP BY user_id ORDER BY c DESC LIMIT 10', (step,))
            rows = cur.fetchall()
            print('exposures per user for step', step, ':', [dict(r) for r in rows])
            cur.execute('''
                SELECT fe.user_id,
                       SUM(CASE WHEN p.is_news THEN 1 ELSE 0 END) AS news_cnt,
                       SUM(CASE WHEN p.is_news THEN 0 ELSE 1 END) AS non_news_cnt,
                       COUNT(*) AS total
                FROM feed_exposures fe
                JOIN posts p ON p.post_id = fe.post_id
                WHERE fe.time_step = ?
                GROUP BY fe.user_id
                ORDER BY total DESC
            ''', (step,))
            print('news/non-news split (top 5):', [dict(r) for r in cur.fetchall()][:5])
            cur.execute('''
                SELECT COUNT(*) AS c FROM (
                    SELECT p.post_id
                    FROM feed_exposures fe
                    JOIN posts p ON p.post_id = fe.post_id
                    JOIN post_timesteps pt ON pt.post_id = p.post_id
                    WHERE fe.time_step = ? AND p.is_news = 1 AND pt.time_step = fe.time_step
                )
            ''', (step,))
            print('current-step news exposures at step', step, ':', cur.fetchone()['c'])

    conn.close()

if __name__ == '__main__':
    main()

