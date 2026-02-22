#!/usr/bin/env python3
"""Monthly memory scan for suspicious patterns."""
import re, json, datetime, urllib.request
from pathlib import Path

ROOT = Path('/Users/andy/.openclaw/workspace')
REPORT_DIR = ROOT / 'poc' / 'security'

cred_path = ROOT / 'credentials' / 'telegram_bot.json'
try:
    with open(cred_path) as f:
        cred = json.load(f)
        bot_token = cred.get('bot_token', cred.get('token', ''))
except: bot_token = ''
CHAT_ID = '5510621427'

SUSPICIOUS = [
    ('Credential', re.compile(r'(?:password|secret|token|api_key)\s*[=:]\s*["\']?[A-Za-z0-9_/+=-]{8,}')),
    ('Bot Token', re.compile(r'\d{8,10}:AA[A-Za-z0-9_-]{33,}')),
    ('Injection Marker', re.compile(r'(?:System:|Ignore previous|You are now|Act as|New instructions:)', re.IGNORECASE)),
    ('Base64 Payload', re.compile(r'[A-Za-z0-9+/]{40,}={0,2}')),
    ('PII Email', re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')),
]

def send_telegram(text):
    if not bot_token: return
    url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
    data = json.dumps({'chat_id': CHAT_ID, 'text': text, 'parse_mode': 'HTML'}).encode()
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    try: urllib.request.urlopen(req, timeout=10)
    except: pass

def scan():
    findings = []
    mem_dir = ROOT / 'memory'
    targets = list(mem_dir.glob('*.md')) if mem_dir.exists() else []
    targets.append(ROOT / 'MEMORY.md')

    for fp in targets:
        if not fp.exists(): continue
        try:
            txt = fp.read_text(errors='ignore')
        except: continue
        rel = str(fp.relative_to(ROOT))
        for name, pat in SUSPICIOUS:
            if name == 'PII Email': continue  # skip email, too many false positives in memory
            for m in pat.finditer(txt):
                line = txt[:m.start()].count('\n') + 1
                snippet = txt[max(0,m.start()-20):m.end()+20].replace('\n',' ')[:100]
                findings.append({
                    'type': name,
                    'file': rel,
                    'line': line,
                    'snippet': snippet,
                })

    now = datetime.datetime.now().isoformat()
    report = {'generated_at': now, 'type': 'memory_scan', 'findings': findings}
    report_path = REPORT_DIR / 'memory_scan_latest.json'
    with open(report_path, 'w') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    if findings:
        msg = f"<b>🧠 월간 메모리 보안 스캔</b>\n시각: {now[:19]}\n\n"
        msg += f"발견: {len(findings)}건\n\n"
        for f in findings[:10]:
            msg += f"⚠️ [{f['type']}] {f['file']}:{f['line']}\n   {f['snippet']}\n\n"
    else:
        msg = f"<b>🧠 월간 메모리 보안 스캔</b>\n시각: {now[:19]}\n\n🟢 이상 없음"

    print(msg, flush=True)
    send_telegram(msg)

if __name__ == '__main__':
    scan()
