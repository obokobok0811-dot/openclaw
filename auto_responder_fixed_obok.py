#!/usr/bin/env python3
import time, json, urllib.request, urllib.parse, sys, os

if len(sys.argv) < 2:
    print('Usage: auto_responder_fixed_obok.py <credentials.json>')
    sys.exit(1)
cred_path = sys.argv[1]
with open(cred_path) as f:
    data=json.load(f)
TOKEN = data.get('token') or data.get('bot_token')
if not TOKEN:
    print('No token found in', cred_path)
    sys.exit(1)

offset=None
POLL_INTERVAL=int(os.environ.get('POLL_INTERVAL','5'))
reply_text = '메시지를 잘 받았습니다 — 자세히 알려주시면 도와드리겠습니다.'

print('Starting fixed auto-responder for', cred_path)
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
                if 'message' in u and 'text' in u['message']:
                    m=u['message']
                    chat_id=m['chat']['id']
                    print('Received message, replying fixed text to', chat_id)
                    data=urllib.parse.urlencode({'chat_id':chat_id,'text':reply_text}).encode()
                    try:
                        req=urllib.request.urlopen(f'https://api.telegram.org/bot{TOKEN}/sendMessage', data=data)
                        print('Replied, status', req.getcode())
                    except Exception as e:
                        print('sendMessage failed:', e)
        time.sleep(POLL_INTERVAL)
    except Exception as e:
        print('error:', e)
        time.sleep(5)
