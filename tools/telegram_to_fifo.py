#!/usr/bin/env python3
import os, time, json
FW='workspace/forwarded_messages.jsonl'
FIFO='workspace/telegram_fifo'
last=0
# ensure fifo exists
if not os.path.exists('workspace'):
    os.makedirs('workspace')
if not os.path.exists(FIFO):
    try:
        os.mkfifo(FIFO)
    except Exception:
        pass
# load allowed bots/chat ids
allowed_bots=set()
allowed_chat_ids=set()
try:
    pairing=json.load(open('credentials/telegram_pairing.json',encoding='utf-8'))
    for b in pairing.get('bots',[]):
        if b.get('botName'):
            allowed_bots.add(b.get('botName'))
        if b.get('username'):
            allowed_bots.add(b.get('username'))
    if pairing.get('user_id'):
        allowed_chat_ids.add(str(pairing.get('user_id')))
except Exception:
    pass

# open fifo for writing when there's a reader
while True:
    try:
        if not os.path.exists(FW):
            time.sleep(1)
            continue
        with open(FW,'r',encoding='utf-8') as f:
            lines=f.read().splitlines()
        if len(lines)>last:
            new=lines[last:]
            # only write when FIFO has reader
            try:
                with open(FIFO,'w',encoding='utf-8') as fifo:
                    for l in new:
                        try:
                            obj=json.loads(l)
                            bot=obj.get('bot')
                            chat_id=str(obj.get('chat_id'))
                            if allowed_bots and bot not in allowed_bots and chat_id not in allowed_chat_ids:
                                continue
                            t=obj.get('text','')
                            fifo.write(f"[TG {bot} {chat_id}] {t}\n")
                        except Exception:
                            fifo.write(f"[TG RAW] {l}\n")
                    fifo.flush()
            except BlockingIOError:
                # no readers
                pass
            except Exception:
                pass
            last=len(lines)
        time.sleep(0.5)
    except Exception:
        time.sleep(1)
