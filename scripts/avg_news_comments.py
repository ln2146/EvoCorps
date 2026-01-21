import sqlite3
conn=sqlite3.connect('database/simulation.db')
conn.row_factory=sqlite3.Row
cur=conn.cursor()
cur.execute("SELECT user_id FROM users WHERE user_id<>?", ('agentverse_news',))
users=[r['user_id'] for r in cur.fetchall()]
cur.execute("PRAGMA table_info(comments)")
cols=[r['name'] for r in cur.fetchall()]
has_agent_type = 'agent_type' in cols
counts={}
if users:
    if has_agent_type:
        sql = 'SELECT c.author_id AS uid, COUNT(*) AS cnt FROM comments c JOIN posts p ON p.post_id=c.post_id WHERE p.is_news=1 AND c.author_id IN (%s) AND c.agent_type=\'normal\' GROUP BY c.author_id' % (','.join(['?']*len(users)))
    else:
        sql = 'SELECT c.author_id AS uid, COUNT(*) AS cnt FROM comments c JOIN posts p ON p.post_id=c.post_id WHERE p.is_news=1 AND c.author_id IN (%s) GROUP BY c.author_id' % (','.join(['?']*len(users)))
    for r in conn.execute(sql, users):
        counts[r['uid']] = r['cnt']
per_user=[counts.get(u,0) for u in users]
all_users_avg = (sum(per_user)/len(per_user)) if per_user else 0.0
active=[v for v in per_user if v>0]
active_avg = (sum(active)/len(active)) if active else 0.0
print('users_total:', len(users))
print('commenters_on_news:', len(active))
print('avg_news_comments_per_user_all:', round(all_users_avg,3))
print('avg_news_comments_per_commenter:', round(active_avg,3))
conn.close()
