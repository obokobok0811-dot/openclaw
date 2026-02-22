#!/usr/bin/env python3
import time, json, urllib.request, os

# Forwards updates from Telegram (specific user id) to this session by printing JSON lines to stdout
# Adjust USER_ID to the Telegram user id to forward (set via env FORWARD_USER_ID)

TOKEN=None
try:
    with open('credentials/telegram_bot.json') as f:
        data=json.load(f)
        TOKEN=data.get('bot_token')
except Exception as e:
    print('Could not read token:', e)
    raise

USER_ID=os.environ.get('FORWARD_USER_ID','5510621427')
interval=int(os.environ.get('POLL_INTERVAL','15'))
offset=None

print('Starting forwarder...')
while True:
    try:
        url=f'https://api.telegram.org/bot{TOKEN}/getUpdates'
        if offset:
            url+=f'?offset={offset}'
        with urllib.request.urlopen(url, timeout=30) as r:
            resp=json.load(r)
        if resp.get('ok') and resp.get('result'):
            for u in resp['result']:
                offset = u['update_id'] + 1
                if 'message' in u:
                    m=u['message']
                    if m['from']['id'] == int(USER_ID):
                        out = {
                            'chat_id': m['chat']['id'],
                            'from_id': m['from']['id'],
                            'text': m.get('text',''),
                            'date': m.get('date')
                        }
                        print('FORWARD:', json.dumps(out, ensure_ascii=False))
        time.sleep(interval)
    except Exception as e:
        print('Forwarder error:', e)
        time.sleep(5)
