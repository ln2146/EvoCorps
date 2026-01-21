import sqlite3
import sys

user = sys.argv[1] if len(sys.argv) > 1 else 'user-32daa1'
step = int(sys.argv[2]) if len(sys.argv) > 2 else 1

conn = sqlite3.connect('database/simulation.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Top2 news by engagement
cur.execute('''
SELECT post_id FROM posts WHERE is_news=1 AND (status IS NULL OR status!='taken_down')
ORDER BY (COALESCE(num_comments,0)+COALESCE(num_likes,0)+COALESCE(num_shares,0)) DESC LIMIT 2
''')
top2 = {r['post_id'] for r in cur.fetchall()}

# Current-step news set
cur.execute('''
SELECT p.post_id
FROM posts p JOIN post_timesteps pt ON pt.post_id = p.post_id
WHERE p.is_news=1 AND pt.time_step = ?
''', (step,))
curr = {r['post_id'] for r in cur.fetchall()}

# Mid-engagement news set
cur.execute('''
SELECT post_id FROM posts WHERE is_news=1
AND (COALESCE(num_comments,0)+COALESCE(num_likes,0)+COALESCE(num_shares,0)) BETWEEN 3 AND 10
AND (status IS NULL OR status!='taken_down')
''')
mid = {r['post_id'] for r in cur.fetchall()}

# Exposed posts for user@step
cur.execute('''
SELECT fe.post_id FROM feed_exposures fe JOIN posts p ON p.post_id = fe.post_id
WHERE fe.user_id=? AND fe.time_step=? AND p.is_news=1
''', (user, step))
seen = [r['post_id'] for r in cur.fetchall()]

print('news seen total:', len(seen))
print('in top2:', len([p for p in seen if p in top2]))
print('in current-step:', len([p for p in seen if p in curr]))
print('in mid-engagement:', len([p for p in seen if p in mid]))
others = [p for p in seen if p not in top2 and p not in curr and p not in mid]
print('other news (not in any category):', len(others), others)

conn.close()

