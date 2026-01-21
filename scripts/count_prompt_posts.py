import re
path='temp_reaction_log.jsonl'
with open(path,'r',encoding='utf-8') as f:
    lines=f.read().splitlines()
print('entries:',len(lines))
for idx,ln in enumerate(lines[-12:]):
    m=re.search(r'"user_id":"([^"]+)"', ln)
    uid=m.group(1) if m else 'unknown'
    cnt=len(re.findall(r'post_id:', ln))
    print(idx, uid, cnt)
