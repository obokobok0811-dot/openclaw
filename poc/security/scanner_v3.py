#!/usr/bin/env python3
"""Security scanner v3: scan + Telegram alert + deep-dive support."""
import os, re, json, datetime, sys, urllib.request
from pathlib import Path

ROOT = Path('/Users/andy/.openclaw/workspace')
OUT_DIR = ROOT / 'poc' / 'security'
OUT_DIR.mkdir(parents=True, exist_ok=True)
report_path = OUT_DIR / 'run_latest_report.json'

# Load bot token
cred_path = ROOT / 'credentials' / 'telegram_bot.json'
try:
    with open(cred_path) as f:
        cred = json.load(f)
    bot_token = cred.get('bot_token', cred.get('token', ''))
except Exception:
    bot_token = ''

CHAT_ID = '5510621427'

PATTERNS = {
    'AWS Access Key': re.compile(r'AKIA[0-9A-Z]{16}'),
    'Private Key': re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    'Google API Key': re.compile(r'AIza[0-9A-Za-z_-]{35}'),
    'JWT': re.compile(r'eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}'),
    'Token Assignment': re.compile(r'(?:api_key|secret|token|password)\s*[=:]\s*["\'][A-Za-z0-9_/+=-]{8,}'),
    'Telegram Bot Token': re.compile(r'\d{8,10}:AA[A-Za-z0-9_-]{33,}'),
    'OAuth Client Secret': re.compile(r'(?:client_secret|GOCSPX-)[A-Za-z0-9_-]{20,}'),
    'Generic High Entropy': re.compile(r'(?:SECRET|PRIVATE|CREDENTIAL)[_\s]*[=:]\s*["\']?[A-Za-z0-9_/+=-]{16,}'),
}

SEVERITY_MAP = {
    'AWS Access Key': 'CRITICAL',
    'Private Key': 'CRITICAL',
    'Google API Key': 'CRITICAL',
    'Telegram Bot Token': 'CRITICAL',
    'OAuth Client Secret': 'CRITICAL',
    'JWT': 'HIGH',
    'Token Assignment': 'HIGH',
    'Generic High Entropy': 'MEDIUM',
}

SKIP_DIRS = {'.git', 'node_modules', '.venv', 'venv', '__pycache__', 'credentials'}
SKIP_FILES = {'run_latest_report.json', 'scanner_v3.py', 'scanner_v2.py', 'run_scanner.py'}
SKIP_EXT = {'.pyc', '.png', '.jpg', '.jpeg', '.gif', '.pdf', '.zip', '.7z', '.dmg',
            '.ico', '.woff', '.ttf', '.db', '.sqlite', '.index', '.ids', '.jsonl'}
MAX_FILE_SIZE = 100_000

def send_telegram(text):
    if not bot_token:
        print('WARN: no bot token, skipping Telegram alert', flush=True)
        return
    url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
    data = json.dumps({'chat_id': CHAT_ID, 'text': text, 'parse_mode': 'HTML'}).encode()
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f'WARN: Telegram send failed: {e}', flush=True)

def scan():
    findings = []
    files_scanned = 0
    print('Scanning...', flush=True)

    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fname in filenames:
            fp = Path(dirpath) / fname
            if fp.suffix.lower() in SKIP_EXT:
                continue
            if fp.name in SKIP_FILES:
                continue
            try:
                sz = fp.stat().st_size
                if sz > MAX_FILE_SIZE or sz == 0:
                    continue
                txt = fp.read_text(errors='ignore')
            except Exception:
                continue
            files_scanned += 1
            rel = str(fp.relative_to(ROOT))
            for name, pat in PATTERNS.items():
                for m in pat.finditer(txt):
                    ctx_start = max(0, m.start() - 30)
                    ctx_end = min(len(txt), m.end() + 30)
                    snippet = txt[ctx_start:ctx_end].replace('\n', ' ').strip()
                    line_num = txt[:m.start()].count('\n') + 1
                    sev = SEVERITY_MAP.get(name, 'MEDIUM')
                    findings.append({
                        'id': len(findings) + 1,
                        'severity': sev,
                        'type': name,
                        'file': rel,
                        'line': line_num,
                        'match_preview': m.group(0)[:60],
                        'context': snippet[:200],
                        'recommendation': get_recommendation(name),
                    })
    return files_scanned, findings

def get_recommendation(finding_type):
    recs = {
        'AWS Access Key': 'Rotate this key immediately via AWS IAM console.',
        'Private Key': 'Move to a secure vault or encrypted storage. Never commit to repos.',
        'Google API Key': 'Restrict key scope in Google Cloud Console or rotate.',
        'Telegram Bot Token': 'Revoke via @BotFather and regenerate if exposed.',
        'OAuth Client Secret': 'Rotate in provider console. Check for unauthorized access.',
        'JWT': 'Verify this is not a long-lived token. Check expiry and scope.',
        'Token Assignment': 'Move to environment variable or secrets manager.',
        'Generic High Entropy': 'Review if this is a real credential. Move to secure storage if so.',
    }
    return recs.get(finding_type, 'Review and remediate as appropriate.')

def build_report(files_scanned, findings):
    now = datetime.datetime.now().isoformat()
    critical = [f for f in findings if f['severity'] == 'CRITICAL']
    high = [f for f in findings if f['severity'] == 'HIGH']
    medium = [f for f in findings if f['severity'] == 'MEDIUM']
    report = {
        'generated_at': now,
        'root': str(ROOT),
        'files_scanned': files_scanned,
        'total_findings': len(findings),
        'summary': {'critical': len(critical), 'high': len(high), 'medium': len(medium)},
        'findings': findings,
    }
    with open(report_path, 'w', encoding='utf-8') as rf:
        json.dump(report, rf, ensure_ascii=False, indent=2)
    return report

def format_digest(report):
    s = report['summary']
    lines = [
        f"<b>🔒 보안 스캔 리포트</b>",
        f"시각: {report['generated_at'][:19]}",
        f"스캔 파일: {report['files_scanned']}개",
        f"",
        f"<b>요약:</b>",
        f"🔴 Critical: {s['critical']}건",
        f"🟠 High: {s['high']}건",
        f"🟡 Medium: {s['medium']}건",
        f"",
    ]
    if report['total_findings'] == 0:
        lines.append("🟢 발견된 보안 이슈 없음. 워크스페이스 깨끗합니다.")
    else:
        lines.append("<b>발견 항목:</b>")
        for f in report['findings']:
            icon = {'CRITICAL': '🔴', 'HIGH': '🟠', 'MEDIUM': '🟡'}.get(f['severity'], '⚪')
            lines.append(f"{icon} <b>#{f['id']}</b> [{f['severity']}] {f['type']}")
            lines.append(f"   파일: <code>{f['file']}:{f['line']}</code>")
            lines.append(f"   권고: {f['recommendation']}")
            lines.append("")
        lines.append("\"#n 더보기\"로 상세 근거를 요청하세요.")
    return '\n'.join(lines)

def format_deep_dive(finding):
    lines = [
        f"<b>🔍 #{finding['id']} 상세 보기</b>",
        f"",
        f"<b>유형:</b> {finding['type']}",
        f"<b>심각도:</b> {finding['severity']}",
        f"<b>파일:</b> <code>{finding['file']}</code>",
        f"<b>라인:</b> {finding['line']}",
        f"<b>매칭:</b> <code>{finding['match_preview'][:40]}...</code>",
        f"<b>컨텍스트:</b>",
        f"<code>{finding['context']}</code>",
        f"",
        f"<b>권고:</b> {finding['recommendation']}",
    ]
    return '\n'.join(lines)

if __name__ == '__main__':
    # Deep dive mode: python3 scanner_v3.py deepdive 3
    if len(sys.argv) >= 3 and sys.argv[1] == 'deepdive':
        try:
            fid = int(sys.argv[2])
            with open(report_path) as f:
                report = json.load(f)
            match = [x for x in report['findings'] if x['id'] == fid]
            if match:
                msg = format_deep_dive(match[0])
                print(msg, flush=True)
                send_telegram(msg)
            else:
                print(f'Finding #{fid} not found in latest report.', flush=True)
        except Exception as e:
            print(f'Error: {e}', flush=True)
        sys.exit(0)

    # Normal scan
    files_scanned, findings = scan()
    report = build_report(files_scanned, findings)
    digest = format_digest(report)

    print(digest, flush=True)
    print(f'\nReport saved: {report_path}', flush=True)

    # Send digest to Telegram
    send_telegram(digest)

    # Immediate alert for critical findings
    critical = [f for f in findings if f['severity'] == 'CRITICAL']
    if critical:
        alert = f"⚠️ <b>긴급 보안 알림: {len(critical)}건의 CRITICAL 발견!</b>\n\n"
        for c in critical:
            alert += f"🔴 #{c['id']} {c['type']} in <code>{c['file']}:{c['line']}</code>\n"
        alert += "\n즉시 확인이 필요합니다."
        send_telegram(alert)

    print(f'\nDone. {files_scanned} files, {len(findings)} findings.', flush=True)
