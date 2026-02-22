#!/usr/bin/env python3
"""Weekly repo size monitor."""
import os, json, datetime, urllib.request
from pathlib import Path

ROOT = Path('/Users/andy/.openclaw/workspace')
REPORT_DIR = ROOT / 'poc' / 'security'
HISTORY = REPORT_DIR / 'repo_size_history.jsonl'

cred_path = ROOT / 'credentials' / 'telegram_bot.json'
try:
    with open(cred_path) as f:
        cred = json.load(f)
        bot_token = cred.get('bot_token', cred.get('token', ''))
except: bot_token = ''
CHAT_ID = '5510621427'

def send_telegram(text):
    if not bot_token: return
    url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
    data = json.dumps({'chat_id': CHAT_ID, 'text': text, 'parse_mode': 'HTML'}).encode()
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    try: urllib.request.urlopen(req, timeout=10)
    except: pass

def get_size(path):
    total = 0
    for dirpath, dirnames, filenames in os.walk(path):
        dirnames[:] = [d for d in dirnames if d not in {'.git', 'node_modules', '.venv', 'venv'}]
        for f in filenames:
            fp = Path(dirpath) / f
            try: total += fp.stat().st_size
            except: pass
    return total

def find_large_files(path, threshold=5_000_000):
    large = []
    for dirpath, dirnames, filenames in os.walk(path):
        dirnames[:] = [d for d in dirnames if d not in {'.git', 'node_modules', '.venv', 'venv'}]
        for f in filenames:
            fp = Path(dirpath) / f
            try:
                sz = fp.stat().st_size
                if sz > threshold:
                    large.append((str(fp.relative_to(ROOT)), sz))
            except: pass
    return sorted(large, key=lambda x: -x[1])[:10]

def check():
    now = datetime.datetime.now().isoformat()
    current_size = get_size(ROOT)
    large_files = find_large_files(ROOT)

    entry = {'timestamp': now, 'size_bytes': current_size}

    # Read history
    prev_size = None
    if HISTORY.exists():
        lines = HISTORY.read_text().strip().split('\n')
        if lines and lines[-1]:
            try:
                prev = json.loads(lines[-1])
                prev_size = prev.get('size_bytes')
            except: pass

    # Append to history
    with open(HISTORY, 'a') as f:
        f.write(json.dumps(entry) + '\n')

    # Calculate growth
    alerts = []
    if prev_size and prev_size > 0:
        growth = (current_size - prev_size) / prev_size * 100
        if growth > 20:
            alerts.append(f'⚠️ Repo size grew {growth:.1f}% since last check (possible data leak)')
    if large_files:
        alerts.append(f'📦 Large files (>5MB):')
        for name, sz in large_files:
            alerts.append(f'   {name}: {sz/1_000_000:.1f}MB')

    size_mb = current_size / 1_000_000

    if alerts:
        msg = f"<b>📊 주간 레포 사이즈 모니터링</b>\n시각: {now[:19]}\n현재: {size_mb:.1f}MB\n\n" + '\n'.join(alerts)
    else:
        msg = f"<b>📊 주간 레포 사이즈 모니터링</b>\n시각: {now[:19]}\n현재: {size_mb:.1f}MB\n\n🟢 이상 없음"

    print(msg, flush=True)
    send_telegram(msg)

if __name__ == '__main__':
    check()
