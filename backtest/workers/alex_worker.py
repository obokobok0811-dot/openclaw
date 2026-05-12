#!/usr/bin/env python3
import time, json, os, re
from datetime import datetime

LOG = '/Users/andy/.openclaw/workspace/backtest/workers/alex.log'
CMD = '/Users/andy/.openclaw/workspace/backtest/workers/commands_alex.json'
RAW_DIR = '/Users/andy/.openclaw/workspace/dart_raw'
os.makedirs(os.path.dirname(LOG), exist_ok=True)
os.makedirs(RAW_DIR, exist_ok=True)

def write_log(obj):
    with open(LOG,'a') as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")

def load_cmds():
    if not os.path.exists(CMD):
        return []
    try:
        with open(CMD) as f:
            data = json.load(f)
        return data.get('commands', [])
    except Exception:
        return []

def save_cmds(cmds):
    with open(CMD,'w') as f:
        json.dump({'commands':cmds}, f)

# simple extraction of key phrases from saved raw HTML files
def REDACTED(path):
    try:
        text = open(path,'rb').read().decode('utf-8', errors='ignore')
    except Exception:
        return None
    # look for keywords
    findings = {}
    patterns = {
        'share_cancel':'(자사주\s*소각|자사주\s*취득|주주환원)',
        'board_resolution':'(이사회\s*결의|이사회\s*결정)',
        'take_or_pay':'(Take[-\s]?or[-\s]?Pay|최소\s*물량\s*보장|최소\s*발주)'
    }
    for k,p in patterns.items():
        m = re.search(p, text, re.IGNORECASE)
        findings[k] = bool(m)
    return findings

write_log({'ts':datetime.now().isoformat(),'agent':'Alex','event':'start'})
while True:
    cmds = load_cmds()
    if cmds:
        cmd = cmds.pop(0)
        save_cmds(cmds)
        question = cmd.get('question','')
        write_log({'ts':datetime.now().isoformat(),'agent':'Alex','event':'cmd_received','question':question})
        # if command asks to process a saved raw file acptno, find file
        m = re.search(r'([0-9]{8,})', question)
        acptno = m.group(1) if m else None
        if acptno:
            # find latest file matching acptno in RAW_DIR
            candidates = [f for f in os.listdir(RAW_DIR) if f.startswith(acptno+'_')]
            if candidates:
                candidates.sort()
                path = os.path.join(RAW_DIR, candidates[-1])
                findings = REDACTED(path)
                write_log({'ts':datetime.now().isoformat(),'agent':'Alex','event':'extracted','acptno':acptno,'path':path,'findings':findings})
            else:
                write_log({'ts':datetime.now().isoformat(),'agent':'Alex','event':'no_raw_found','acptno':acptno})
        else:
            write_log({'ts':datetime.now().isoformat(),'agent':'Alex','event':'no_acptno','question':question})
        time.sleep(1.5)
    else:
        write_log({'ts':datetime.now().isoformat(),'agent':'Alex','status':'idle','note':'waiting'})
        time.sleep(1.5)
