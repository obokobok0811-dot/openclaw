#!/usr/bin/env python3
import json,glob,os,datetime
from pathlib import Path

AGENT='obok'
SESS_DIR=Path(f'/Users/andy/.openclaw/agents/{AGENT}/sessions')
OUT_DIR=Path('/Users/andy/Documents/Obsidian/Obsidian Vault/OpenClaw/Sessions')
OUT_DIR.mkdir(parents=True, exist_ok=True)

now=datetime.datetime.now()
date_dir=OUT_DIR/now.strftime('%Y-%m-%d')
# ensure date folder
date_dir=OUT_DIR/now.strftime('%Y-%m-%d')
# We'll write into OpenClaw/Sessions/YYYY-MM-DD/auto_saved.md
day_dir=OUT_DIR/now.strftime('%Y-%m-%d')
Path(day_dir).mkdir(parents=True, exist_ok=True)
out_path=Path(day_dir)/'auto_saved.md'

seen=set()
if not SESS_DIR.exists():
    # nothing to do
    print('no sessions dir')
    raise SystemExit

for f in sorted(glob.glob(str(SESS_DIR)+'/*.jsonl')):
    try:
        with open(f,'r') as fh:
            for line in fh:
                try:
                    obj=json.loads(line)
                except:
                    continue
                mid=obj.get('message_id') or obj.get('id') or obj.get('ts')
                if not mid or mid in seen:
                    continue
                seen.add(mid)
                t=obj.get('ts') or obj.get('timestamp') or obj.get('time')
                who=obj.get('author') or obj.get('accountId') or obj.get('role')
                text=obj.get('text') or obj.get('message') or obj.get('content')
                if not text:
                    continue
                # append to out
                with open(out_path,'a') as out:
                    out.write(f"- {t} | {who}: {text}\n")
    except Exception as e:
        continue
print('done')
