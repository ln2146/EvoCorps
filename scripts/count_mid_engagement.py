import sqlite3

conn = sqlite3.connect('database/simulation.db')
cur = conn.cursor()
cur.execute('''
    SELECT COUNT(*) FROM posts p
    WHERE p.is_news=1
      AND (COALESCE(p.num_comments,0)+COALESCE(p.num_likes,0)+COALESCE(p.num_shares,0)) BETWEEN 3 AND 10
      AND (p.status IS NULL OR p.status != 'taken_down')
''')
print('mid engagement news total available:', cur.fetchone()[0])
conn.close()

