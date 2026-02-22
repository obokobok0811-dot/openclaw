#!/usr/bin/env python3
import time, re, os, sys, json, urllib.request, urllib.parse

LOG_FILES = [
    'logs/replyer.log',
    'logs/forwarder_shin.log',
    'logs/auto_responder_zzuvi.log'
]

# load token and chat id
try:
    cred = json.load(open('credentials/telegram_bot.json', encoding='utf-8'))
    TOKEN = cred.get('bot_token')
except Exception as e:
    print('Could not load token:', e)
    sys.exit(1)

CHAT_ID = '5510621427'

# sensitive patterns to mask
PATTERNS = [
    re.compile(r"\b[0-9]{8,}\:[A-Za-z0-9_-]{30,}\b"),  # bot token like
    re.compile(r'bot_token"\s*:\s*"[^\"]+"'),
    re.compile(r"[A-Za-z0-9._%+-]+\@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16,}\b"),
    re.compile(r"password\W*[:=]\W*\S+", re.I),
]

LAST_POS = {}
for f in LOG_FILES:
    try:
        LAST_POS[f] = os.path.getsize(f)
    except Exception:
        LAST_POS[f] = 0


def mask_line(line):
    s = line
    for p in PATTERNS:
        s = p.sub('***', s)
    # also mask long tokens groups
    s = re.sub(r"[A-Za-z0-9_-]{40,}", '***', s)
    return s


def send_telegram(text):
    try:
        data = urllib.parse.urlencode({'chat_id': CHAT_ID, 'text': text}).encode()
        urllib.request.urlopen(f'https://api.telegram.org/bot{TOKEN}/sendMessage', data=data, timeout=10)
    except Exception as e:
        print('failed send', e)


print('Starting log tailer -> telegram for files:', LOG_FILES)
while True:
    for f in LOG_FILES:
        try:
            if not os.path.exists(f):
                continue
            sz = os.path.getsize(f)
            last = LAST_POS.get(f, 0)
            if sz > last:
                with open(f, 'r', encoding='utf-8', errors='ignore') as fh:
                    fh.seek(last)
                    for line in fh:
                        line=line.rstrip('\n')
                        ml = mask_line(line)
                        if ml.strip():
                            send_telegram(f'[{os.path.basename(f)}] {ml}')
                LAST_POS[f] = fh.tell()
        except Exception as e:
            print('error tailing', f, e)
    time.sleep(1)
