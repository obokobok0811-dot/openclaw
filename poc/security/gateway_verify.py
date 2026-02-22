#!/usr/bin/env python3
"""Weekly gateway security verification."""
import subprocess, json, datetime, urllib.request
from pathlib import Path

ROOT = Path('/Users/andy/.openclaw/workspace')
REPORT_DIR = ROOT / 'poc' / 'security'
REPORT_DIR.mkdir(parents=True, exist_ok=True)

cred_path = ROOT / 'credentials' / 'telegram_bot.json'
try:
    with open(cred_path) as f:
        cred = json.load(f)
        bot_token = cred.get('bot_token', cred.get('token', ''))
except Exception:
    bot_token = ''
CHAT_ID = '5510621427'

def send_telegram(text):
    if not bot_token: return
    url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
    data = json.dumps({'chat_id': CHAT_ID, 'text': text, 'parse_mode': 'HTML'}).encode()
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    try: urllib.request.urlopen(req, timeout=10)
    except: pass

def run(cmd):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        return r.stdout.strip()
    except: return ''

def check():
    findings = []
    now = datetime.datetime.now().isoformat()

    # 1. Check gateway config for localhost binding
    gw_conf = run("cat /Users/andy/.openclaw/config.json 2>/dev/null || echo '{}'")
    try:
        conf = json.loads(gw_conf)
        bind = conf.get('gateway', {}).get('bind', 'unknown')
        if bind not in ('loopback', 'localhost', '127.0.0.1'):
            findings.append(f'⚠️ Gateway bind is "{bind}" (expected loopback)')
    except:
        findings.append('⚠️ Could not parse gateway config')

    # 2. Check listening ports
    ports = run("lsof -i -P -n | grep LISTEN 2>/dev/null || ss -tlnp 2>/dev/null || echo 'N/A'")
    if ports and ports != 'N/A':
        port_lines = ports.split('\n')
        suspicious = [l for l in port_lines if '0.0.0.0' in l or '::' in l]
        if suspicious:
            findings.append(f'⚠️ {len(suspicious)} services listening on all interfaces')
            for s in suspicious[:5]:
                findings.append(f'   {s[:100]}')

    # 3. Check credentials permissions
    cred_dir = ROOT / 'credentials'
    if cred_dir.exists():
        for f in cred_dir.iterdir():
            mode = oct(f.stat().st_mode)[-3:]
            if mode != '600':
                findings.append(f'⚠️ {f.name} has permissions {mode} (should be 600)')

    # 4. Check .gitignore
    gitignore = ROOT / '.gitignore'
    if gitignore.exists():
        content = gitignore.read_text()
        for pattern in ['.env', 'credentials/', '*.key', '*.pem']:
            if pattern not in content:
                findings.append(f'⚠️ .gitignore missing: {pattern}')
    else:
        findings.append('⚠️ No .gitignore found')

    report = {
        'generated_at': now,
        'type': 'gateway_verification',
        'findings_count': len(findings),
        'findings': findings,
    }

    report_path = REPORT_DIR / 'gateway_verify_latest.json'
    with open(report_path, 'w') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # Telegram report
    if findings:
        msg = f"<b>🛡️ 주간 게이트웨이 보안 검증</b>\n시각: {now[:19]}\n\n"
        msg += f"발견: {len(findings)}건\n\n"
        msg += '\n'.join(findings)
    else:
        msg = f"<b>🛡️ 주간 게이트웨이 보안 검증</b>\n시각: {now[:19]}\n\n🟢 이상 없음"

    print(msg, flush=True)
    send_telegram(msg)

if __name__ == '__main__':
    check()
