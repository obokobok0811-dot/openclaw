#!/usr/bin/env python3
import time, json, urllib.request, urllib.parse, os, sys

# Auto-responder: supports optional credentials file argument
cred_path = 'credentials/telegram_bot.json'
if len(sys.argv) > 1:
    cred_path = sys.argv[1]

TOKEN = None
try:
    with open(cred_path) as f:
        data=json.load(f)
        # support both 'token' and 'bot_token' keys
        TOKEN = data.get('bot_token') or data.get('token')
except Exception as e:
    print('Could not read token from', cred_path, ':', e)
    raise

offset=None
POLL_INTERVAL=int(os.environ.get('POLL_INTERVAL','5'))

print('Starting auto_responder (interval', POLL_INTERVAL, 's) using', cred_path)
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
                    text=m['text'].strip()
                    sender=m['from'].get('first_name')
                    print('Received from', sender, text)
                    lt=text.lower()
                    # simple rules
                    if any(w in lt for w in ['안녕','hi','hello','hey']):
                        reply=f'안녕하세요 {sender}님! 무엇을 도와드릴까요?'
                    elif any(w in lt for w in ['고마','감사']):
                        reply='천만에요 — 도움이 되어 기쁩니다.'
                    elif any(w in lt for w in ['시간','몇시','언제']):
                        import datetime
                        reply = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    elif any(w in lt for w in ['재설정','초기화','다시 시작']):
                        reply='요청하신 작업을 진행하려면 자세히 알려주세요. 어떤 걸 다시 시작할까요?'
                    else:
                        # For 'obok' enforce no follow-up questions: produce a concise, final answer without question marks
                        bot_label = data.get('botName','').lower()
                        def obok_answer(txt):
                            t = txt.strip()
                            t_clean = t.replace('?', '').replace('？', '')
                            if len(t_clean) == 0:
                                return ''
                            if len(t_clean.split()) <= 6:
                                return t_clean
                            if len(t_clean) > 120:
                                return t_clean[:120].rstrip() + '...'
                            return t_clean
                        if 'obok' in bot_label:
                            reply = obok_answer(text)
                        else:
                            # default: echo concise content without prefixes
                            short = text.strip()
                            if len(short) > 200:
                                short = short[:200].rstrip() + '...'
                            reply = short
                    # If reply would repeat the user's exact message or is empty, skip sending
                    if reply is None or reply.strip() == '' or reply.strip() == text.strip():
                        print('Skipping send: empty or duplicate')
                    else:
                        data=urllib.parse.urlencode({'chat_id':chat_id,'text':reply}).encode()
                        req=urllib.request.urlopen(f'https://api.telegram.org/bot{TOKEN}/sendMessage', data=data)
                        print('Replied, status', req.getcode())
        time.sleep(POLL_INTERVAL)
    except Exception as e:
        print('auto_responder error:', e)
        time.sleep(5)
