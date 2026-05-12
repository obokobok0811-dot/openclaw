#!/usr/bin/env python3
import time, json, os
FW='workspace/forwarded_messages.jsonl'
OUT='logs/terminal_replica.log'
last=0
if not os.path.exists('logs'):
    os.makedirs('logs')

# No filter: send all forwarded Telegram messages to terminal
allowed_bots = None
allowed_chat_ids = None

while True:
    try:
        if not os.path.exists(FW):
            time.sleep(1)
            continue
        with open(FW,'r',encoding='utf-8') as f:
            lines=f.read().splitlines()
        if len(lines)>last:
            new=lines[last:]
            with open(OUT,'a',encoding='utf-8') as out:
                for l in new:
                    try:
                        obj=json.loads(l)
                        bot = obj.get('bot')
                        chat_id = str(obj.get('chat_id'))
                        # check allowed: either bot matches allowed_bots or chat_id is allowed
                        if allowed_bots and bot not in allowed_bots and chat_id not in allowed_chat_ids:
                            continue
                        t=obj.get('text','')
                        s=f"[TELEGRAM {bot} {chat_id}] {t}\n"
                    except Exception:
                        s=f"[TELEGRAM RAW] {l}\n"
                    out.write(s)
                    out.flush()
            last=len(lines)
        time.sleep(1)
    except Exception as e:
        with open(OUT,'a',encoding='utf-8') as out:
            out.write(f'ERROR: {e}\n')
        time.sleep(2)
