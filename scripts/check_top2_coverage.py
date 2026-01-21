import sqlite3

conn = sqlite3.connect('database/simulation.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute('''
SELECT post_id,
       (COALESCE(num_comments,0)+COALESCE(num_likes,0)+COALESCE(num_shares,0)) AS eng
FROM posts WHERE is_news=1 AND (status IS NULL OR status!='taken_down')
ORDER BY eng DESC LIMIT 2
''')
top = [r['post_id'] for r in cur.fetchall()]
print('top2 news:', top)
cur.execute('SELECT DISTINCT user_id FROM feed_exposures WHERE time_step=1')
users = [r['user_id'] for r in cur.fetchall()]
missing = {}
for u in users:
    cur.execute('SELECT post_id FROM feed_exposures WHERE user_id=? AND time_step=1', (u,))
    seen = set(r['post_id'] for r in cur.fetchall())
    miss = [pid for pid in top if pid not in seen]
    if miss:
        missing[u] = miss
print('users missing any top2:', missing)
print('num users:', len(users), 'num missing:', len(missing))
conn.close()

