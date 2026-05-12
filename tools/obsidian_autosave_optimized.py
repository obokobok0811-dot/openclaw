#!/usr/bin/env python3
"""
Lightweight Obsidian autosave optimized for low-impact cron runs.
Behavior:
 - Run frequently (recommended 5m); check sessions dir mtime and last_seen id to avoid work when nothing changed.
 - Use an atomic append-only output file per day.
 - Prevent concurrent runs with a lockfile.
 - Limit messages processed per run (batch_limit).
"""
from pathlib import Path
import json, time, os
import sys

AGENT='obok'
SESS_DIR=Path(f'/Users/andy/.openclaw/agents/{AGENT}/sessions')
OUT_ROOT=Path('/Users/andy/Documents/Obsidian/Obsidian Vault/OpenClaw/Sessions')
STATE_DIR=Path('/Users/andy/.openclaw/workspace/state')
STATE_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE=STATE_DIR/'obs_autosave.state.json'
LOCK_FILE=STATE_DIR/'obs_autosave.lock'
BATCH_LIMIT=200

# simple lock
if LOCK_FILE.exists():
    # avoid overlapping runs
    sys.exit(0)
try:
    LOCK_FILE.write_text(str(os.getpid()))
except Exception:
    sys.exit(0)

def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            return {}
    return {}

def save_state(s):
    tmp=STATE_FILE.with_suffix('.tmp')
    tmp.write_text(json.dumps(s))
    tmp.rename(STATE_FILE)

state=load_state()

try:
    if not SESS_DIR.exists():
        # nothing to do
        sys.exit(0)
    # check dir mtime
    dir_mtime=max((p.stat().st_mtime for p in SESS_DIR.glob('*.jsonl')), default=0)
    last_mtime=state.get('last_mtime',0)
    if dir_mtime<=last_mtime:
        # no change
        sys.exit(0)
    # iterate files and append new messages
    seen=set(state.get('seen_ids',[]))
    now=time.localtime()
    day_dir=OUT_ROOT/ time.strftime('%Y-%m-%d', now)
    day_dir.mkdir(parents=True, exist_ok=True)
    out_path=day_dir/'auto_saved.md'
    processed=0
    # open for append once
    with out_path.open('a') as out:
        for f in sorted(SESS_DIR.glob('*.jsonl')):
            try:
                for line in open(f,'r'):
                    if processed>=BATCH_LIMIT:
                        break
                    try:
                        obj=json.loads(line)
                    except Exception:
                        continue
                    mid=obj.get('message_id') or obj.get('id') or obj.get('ts')
                    if not mid or mid in seen:
                        continue
                    seen.add(mid)
                    t=obj.get('ts') or obj.get('timestamp') or obj.get('time') or time.strftime('%Y-%m-%dT%H:%M:%S')
                    who=obj.get('author') or obj.get('accountId') or obj.get('role') or 'unknown'
                    text=obj.get('text') or obj.get('message') or obj.get('content')
                    if not text:
                        continue
                    # basic sensitive-data scrub: remove long hex-like tokens and emails
                    text=str(text)
                    text = __import__('re').sub(r"[A-Za-z0-9_\-]{20,}", "[REDACTED]", text)
                    text = __import__('re').sub(r"[\w\.-]+@[\w\.-]+", "[REDACTED_EMAIL]", text)
                    out.write(f"- {t} | {who}: {text}\n")
                    processed+=1
            except Exception:
                continue
    # update state
    state['last_mtime']=dir_mtime
    state['seen_ids']=list(seen)[-10000:]  # keep recent ids limited
    save_state(state)
finally:
    try:
        LOCK_FILE.unlink()
    except Exception:
        pass

print('ok')
