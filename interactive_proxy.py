#!/usr/bin/env python3
import time, json, urllib.request, urllib.parse, os, sys

TOKEN=None
try:
    with open('credentials/telegram_bot.json') as f:
        data=json.load(f)
        TOKEN=data.get('bot_token')
except Exception as e:
    print('Could not read token:', e)
    raise

USER_ID=int(os.environ.get('FORWARD_USER_ID','5510621427'))
POLL_INTERVAL=int(os.environ.get('POLL_INTERVAL','3'))
offset=None

print('Interactive proxy started. POLL_INTERVAL=', POLL_INTERVAL)
print('Incoming Telegram messages from user', USER_ID, 'will be forwarded here as:')
print('[Telegram] <timestamp> — <text>')
print('To send a message to Telegram, reply in this assistant chat with: Send: <your message>')
print('To stop proxy, tell the assistant to stop.')

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
                    if m['from']['id']==USER_ID:
                        ts=m.get('date')
                        text=m.get('text','')
                        print('FORWARD:', json.dumps({'chat_id':m['chat']['id'],'from_id':m['from']['id'],'date':ts,'text':text}, ensure_ascii=False))
        time.sleep(POLL_INTERVAL)
    except Exception as e:
        print('Proxy error:', e)
        time.sleep(5)
