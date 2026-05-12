#!/usr/bin/env python3
import time, json, urllib.request, urllib.parse, os

# Simple polling loop: reads token from credentials/telegram_bot.json
TOKEN=None
try:
    with open('credentials/telegram_bot.json') as f:
        data=json.load(f)
        TOKEN=data.get('bot_token')
except Exception as e:
    print('Could not read token:', e)
    raise

if not TOKEN:
    raise SystemExit('No token')

offset=None
print('Starting poller...')
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
                # handle messages
                if 'message' in u and 'text' in u['message']:
                    chat_id = u['message']['chat']['id']
                    text = u['message']['text']
                    print('Received:', chat_id, text)
                    # simple auto-reply
                    reply = '자동응답: 메시지 잘 받았습니다 — 무엇을 도와드릴까요?'
                    data=urllib.parse.urlencode({'chat_id':chat_id,'text':reply}).encode()
                    req=urllib.request.urlopen(f'https://api.telegram.org/bot{TOKEN}/sendMessage', data=data)
                    print('Replied, status:', req.getcode())
        time.sleep(1)
    except Exception as e:
        print('Poller error:', e)
        time.sleep(5)
