#!/usr/bin/env python3
import time, json, urllib.request, urllib.parse, sys, os

if len(sys.argv) < 3:
    print('Usage: forwarder_to_main.py <credentials.json> <user_allowlist_csv>')
    sys.exit(1)
cred_path = sys.argv[1]
allowlist = sys.argv[2].split(',') if sys.argv[2] else []

with open(cred_path) as f:
    data = json.load(f)
TOKEN = data.get('token') or data.get('bot_token')
bot_label = data.get('botName') or os.path.basename(cred_path)

offset = None
POLL_INTERVAL = int(os.environ.get('POLL_INTERVAL','2'))

print('Starting forwarder for', bot_label)
while True:
    try:
        url = f'https://api.telegram.org/bot{TOKEN}/getUpdates'
        if offset:
            url += f'?offset={offset}'
        with urllib.request.urlopen(url, timeout=30) as r:
            resp = json.load(r)
        if resp.get('ok') and resp.get('result'):
            for u in resp['result']:
                offset = u['update_id'] + 1
                if 'message' in u and 'text' in u['message']:
                    m = u['message']
                    chat_id = m['chat']['id']
                    from_id = m['from'].get('id')
                    text = m['text']
                    # only forward if sender in allowlist
                    if allowlist and str(from_id) not in allowlist:
                        print('Skipping message from', from_id)
                        continue
                    # prepare forwarding payload
                    payload = {
                        'source':'telegram',
                        'bot': bot_label,
                        'from_id': from_id,
                        'chat_id': chat_id,
                        'text': text
                    }
                    # write to local file to be picked up by main agent (or could call external API)
                    # append to workspace/forwarded_messages.jsonl
                    out = 'workspace/forwarded_messages.jsonl'
                    with open(out,'a',encoding='utf-8') as of:
                        of.write(json.dumps(payload,ensure_ascii=False) + '\n')
                    print('Forwarded message from', from_id)
        time.sleep(POLL_INTERVAL)
    except Exception as e:
        print('forwarder error:', e)
        time.sleep(5)
