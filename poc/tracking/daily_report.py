#!/usr/bin/env python3
"""
Daily cost report generator.
Runs at end of day, generates report and sends to Telegram.
"""
import json, datetime, urllib.request, sys
sys.path.insert(0, '/Users/andy/.openclaw/workspace')
from poc.tracking.tracker import generate_report, format_report
from pathlib import Path

ROOT = Path('/Users/andy/.openclaw/workspace')
CRED_PATH = ROOT / 'credentials' / 'telegram_bot.json'
REPORT_DIR = ROOT / 'poc' / 'tracking' / 'reports'
REPORT_DIR.mkdir(parents=True, exist_ok=True)

try:
    with open(CRED_PATH) as f:
        cred = json.load(f)
        BOT_TOKEN = cred.get('bot_token', cred.get('token', ''))
except: BOT_TOKEN = ''
CHAT_ID = '5510621427'

def send_telegram(text):
    if not BOT_TOKEN: return
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    data = json.dumps({'chat_id': CHAT_ID, 'text': text}).encode()
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    try: urllib.request.urlopen(req, timeout=10)
    except: pass

def run():
    now = datetime.datetime.now()
    period = sys.argv[1] if len(sys.argv) > 1 else 'daily'

    report = generate_report(period)
    text = format_report(report)

    # Save to file
    fname = f'{period}_{now.strftime("%Y%m%d")}.json'
    with open(REPORT_DIR / fname, 'w') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(text, flush=True)

    # Only send to Telegram if there were calls
    if report['total_calls'] > 0:
        send_telegram(text)

if __name__ == '__main__':
    run()
