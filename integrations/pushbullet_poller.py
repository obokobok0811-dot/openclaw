#!/usr/bin/env python3
import os, time, json, stat
import requests
from datetime import datetime

CRED_DIR = '/Users/andy/.openclaw/workspace/credentials'
PUSH_TOKEN_FILES = [os.path.join(CRED_DIR,'pushbullet_token.txt'), os.path.join(CRED_DIR,'pushbullet_token.json'), os.path.join(CRED_DIR,'token.json')]
OUT_DIR = '/Users/andy/.openclaw/workspace/sms_inbox'
os.makedirs(OUT_DIR, exist_ok=True)
LAST_FILE = os.path.join(OUT_DIR,'last_ts.txt')
PROCESSED_FILE = os.path.join(OUT_DIR,'processed_ids.txt')

# load token from known files without printing
def load_token():
    for p in PUSH_TOKEN_FILES:
        if os.path.exists(p):
            try:
                with open(p,'r') as f:
                    data = f.read().strip()
                # try JSON
                try:
                    j = json.loads(data)
                    # common fields
                    for k in ('access_token','token','api_key','key'):
                        if k in j and j[k]:
                            return j[k]
                    # if single string value
                    for v in j.values():
                        if isinstance(v,str) and len(v)>20:
                            return v
                except Exception:
                    # assume raw token
                    if len(data)>10:
                        return data
            except Exception:
                continue
    return None

TOKEN = load_token()
if not TOKEN:
    print('Pushbullet token not found. Place token in:', PUSH_TOKEN_FILES)
    raise SystemExit(1)

# Try both header styles: Pushbullet supports 'Access-Token' and 'Authorization: Bearer'
HEADERS = {'Access-Token': TOKEN}
HEADERS_BEARER = {'Authorization': f'Bearer {TOKEN}'}
BASE = 'https://api.pushbullet.com/v2/pushes'

# load last timestamp
last_ts = 0.0
if os.path.exists(LAST_FILE):
    try:
        last_ts = float(open(LAST_FILE).read().strip())
    except Exception:
        last_ts = 0.0

processed = set()
if os.path.exists(PROCESSED_FILE):
    try:
        with open(PROCESSED_FILE,'r') as f:
            for line in f:
                processed.add(line.strip())
    except Exception:
        processed=set()

# single run poll
params = {'modified_after': last_ts}
resp = requests.get(BASE, headers=HEADERS, params=params, timeout=20)
resp.raise_for_status()
data = resp.json()
pushes = data.get('pushes',[])
new_last = last_ts
count=0
for p in pushes:
    try:
        pid = p.get('iden') or p.get('id')
        if not pid or pid in processed:
            continue
        # determine text content
        body = p.get('body','') or ''
        title = p.get('title','') or ''
        # some sms may be in 'sms' field
        sms_body = ''
        if 'sms' in p and isinstance(p['sms'], dict):
            sms_body = p['sms'].get('body','')
            body = body or sms_body
        text = (title+' '+body).strip()
        # filter for 현대카드 (Korean) or HyundaiCard
        if '현대카드' in text or 'HyundaiCard' in text or 'Hyundai Card' in text:
            out = {
                'id': pid,
                'timestamp': p.get('modified', time.time()),
                'title': title,
                'body': body,
                'raw': p
            }
            fn = os.path.join(OUT_DIR, f"hyundaicard_{pid}.json")
            with open(fn,'w') as f:
                json.dump(out, f, ensure_ascii=False, indent=2)
            # append to a jsonl log
            with open(os.path.join(OUT_DIR,'hyundaicard.jsonl'),'a') as f:
                f.write(json.dumps(out, ensure_ascii=False)+'\n')
            count+=1
        processed.add(pid)
        # update new_last to modified
        mod = p.get('modified')
        if mod:
            try:
                new_last = max(new_last, float(mod))
            except:
                pass
    except Exception:
        continue

# persist state
with open(PROCESSED_FILE,'w') as f:
    for pid in processed:
        f.write(pid+'\n')
with open(LAST_FILE,'w') as f:
    f.write(str(new_last))

print('Done. New matches:', count)
