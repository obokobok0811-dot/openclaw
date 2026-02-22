#!/usr/bin/env python3
import time, json, os
FW='workspace/forwarded_messages.jsonl'
PEND='workspace/pending_commands.jsonl'
FIFO='workspace/telegram_fifo'
last=0
if not os.path.exists('workspace'):
    os.makedirs('workspace')
# ensure pending file
open(PEND,'a').close()
while True:
    try:
        if not os.path.exists(FW):
            time.sleep(1); continue
        with open(FW,'r',encoding='utf-8') as f:
            lines=f.read().splitlines()
        if len(lines)>last:
            new=lines[last:]
            for l in new:
                try:
                    obj=json.loads(l)
                    text=obj.get('text','')
                    if text.strip().startswith('CMD:'):
                        cmd=text.strip()[4:].strip()
                        entry={'id':int(time.time()*1000),'cmd':cmd,'from':obj.get('from_id'),'chat':obj.get('chat_id')}
                        with open(PEND,'a',encoding='utf-8') as p:
                            p.write(json.dumps(entry,ensure_ascii=False)+'\n')
                        # also notify on FIFO for review
                        try:
                            with open(FIFO,'w',encoding='utf-8') as fifo:
                                fifo.write(f"[PENDING_CMD {entry['id']}] {entry['cmd']}\n")
                        except Exception:
                            pass
                except Exception:
                    pass
            last=len(lines)
        time.sleep(0.5)
    except Exception:
        time.sleep(1)
