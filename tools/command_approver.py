#!/usr/bin/env python3
import os,sys,json,subprocess
FIFO_APPROVER='workspace/command_approver_fifo'
PEND='workspace/pending_commands.jsonl'
OUT_DIR='workspace/command_outputs'
if not os.path.exists('workspace'): os.makedirs('workspace')
if not os.path.exists(OUT_DIR): os.makedirs(OUT_DIR)
if not os.path.exists(FIFO_APPROVER):
    try: os.mkfifo(FIFO_APPROVER)
    except Exception: pass
print('Approver listening on',FIFO_APPROVER)
while True:
    try:
        with open(FIFO_APPROVER,'r',encoding='utf-8') as fh:
            for line in fh:
                line=line.strip()
                if not line: continue
                # expected: APPROVE <id>
                parts=line.split(None,1)
                if len(parts)<2: continue
                cmd, arg = parts[0].upper(), parts[1]
                if cmd!='APPROVE': continue
                approve_id = arg.strip()
                # find in pending
                found=None
                lines=[]
                with open(PEND,'r',encoding='utf-8') as p:
                    lines=p.read().splitlines()
                newlines=[]
                for l in lines:
                    try:
                        entry=json.loads(l)
                        if str(entry.get('id'))==approve_id:
                            found=entry
                        else:
                            newlines.append(l)
                    except Exception:
                        newlines.append(l)
                if not found:
                    print('not found',approve_id)
                    continue
                # overwrite pending without approved
                with open(PEND,'w',encoding='utf-8') as p:
                    for nl in newlines: p.write(nl+'\n')
                # execute command (careful)
                try:
                    res = subprocess.run(found['cmd'], shell=True, capture_output=True, text=True, timeout=60)
                    out = res.stdout + '\n' + res.stderr
                except Exception as e:
                    out = f'EXEC ERROR: {e}'
                outpath=os.path.join(OUT_DIR, f"{approve_id}.txt")
                with open(outpath,'w',encoding='utf-8') as o:
                    o.write(out)
                # also write to terminal fifo for visibility
                try:
                    with open('workspace/telegram_fifo','w',encoding='utf-8') as tf:
                        tf.write(f"[CMD_RESULT {approve_id}]\n{out}\n")
                except Exception:
                    pass
    except Exception:
        import time; time.sleep(1)
