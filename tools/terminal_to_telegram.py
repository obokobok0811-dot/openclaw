#!/usr/bin/env python3
import os,sys,json,urllib.request,urllib.parse
FIFO_IN='workspace/terminal_to_telegram_fifo'
# ensure workspace
if not os.path.exists('workspace'):
    os.makedirs('workspace')
# create fifo if missing
if not os.path.exists(FIFO_IN):
    try:
        os.mkfifo(FIFO_IN)
    except Exception:
        pass
# load token and default chat id from pairing
try:
    cred=json.load(open('credentials/telegram_bot.json',encoding='utf-8'))
    TOKEN=cred.get('bot_token')
except Exception as e:
    print('missing token',e)
    sys.exit(1)
# determine default target chat id from pairing
CHAT_ID=None
try:
    pairing=json.load(open('credentials/telegram_pairing.json',encoding='utf-8'))
    if pairing.get('user_id'):
        CHAT_ID=str(pairing.get('user_id'))
except Exception:
    pass
if CHAT_ID is None:
    print('No chat id found in pairing; please provide chat id in pairing file.')
    sys.exit(1)

print('Listening on',FIFO_IN,"-> Telegram chat",CHAT_ID)
# open fifo and read lines to send
while True:
    try:
        with open(FIFO_IN,'r',encoding='utf-8') as fh:
            for line in fh:
                line=line.rstrip('\n')
                if not line.strip():
                    continue
                # allow optional prefix "CHAT:<id> " to override
                target=CHAT_ID
                text=line
                if line.startswith('CHAT:'):
                    parts=line.split(' ',1)
                    if len(parts)>1:
                        prefix=parts[0]
                        try:
                            target=prefix.split(':',1)[1]
                            text=parts[1]
                        except Exception:
                            text=parts[1]
                data=urllib.parse.urlencode({'chat_id':target,'text':text}).encode()
                try:
                    urllib.request.urlopen(f'https://api.telegram.org/bot{TOKEN}/sendMessage', data=data, timeout=10)
                except Exception as e:
                    print('send failed',e)
    except Exception as e:
        # wait and retry
        import time
        time.sleep(1)
