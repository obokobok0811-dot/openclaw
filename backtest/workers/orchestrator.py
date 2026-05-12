#!/usr/bin/env python3
import json, time, os
# Orchestrator for Naomi (main), Alex, Amos workers.
# Dispatches commands to workers via commands_*.json and watches logs for responses.
BASE='/Users/andy/.openclaw/workspace/backtest/workers'
CMD_ALEX=os.path.join(BASE,'commands_alex.json')
CMD_AMOS=os.path.join(BASE,'commands_amos.json')
LOG_ALEX=os.path.join(BASE,'alex.log')
LOG_AMOS=os.path.join(BASE,'amos.log')

def push_command(cmdfile, question):
    data={'commands':[]}
    if os.path.exists(cmdfile):
        try:
            data=json.load(open(cmdfile))
        except Exception:
            data={'commands':[]}
    data['commands'].append({'question':question})
    open(cmdfile,'w').write(json.dumps(data))

def tail_log(path, last_pos=0):
    if not os.path.exists(path):
        return last_pos, []
    with open(path,'r') as f:
        f.seek(last_pos)
        lines=f.read().splitlines()
        pos=f.tell()
    return pos, lines

# dispatch example tasks
push_command(CMD_ALEX, 'Fetch DART/KRX 공시 list for company=대우건설 from 2025-11-01 to 2026-05-10; return matching 공시번호 list')
push_command(CMD_ALEX, 'Fetch and save 원문 for 공시번호=20251224000042 if available')
push_command(CMD_AMOS, 'Fetch DART/KRX 공시 list for company=SK스퀘어 from 2025-11-01 to 2026-05-10; return 이사회/자사주/상장예비심사 공시 ids')

print('Dispatched initial jobs to Alex and Amos')
# monitor logs for a short while
la=0; lb=0
for _ in range(60):
    la, lines_a = tail_log(LOG_ALEX, la)
    lb, lines_b = tail_log(LOG_AMOS, lb)
    for l in lines_a:
        print('A>', l)
    for l in lines_b:
        print('M>', l)
    time.sleep(1)
print('Orchestrator finished short watch')
