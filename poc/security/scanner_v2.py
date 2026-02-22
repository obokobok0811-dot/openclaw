#!/usr/bin/env python3
"""Lightweight security scanner - single pass, no hanging."""
import os, re, json, datetime, sys
from pathlib import Path

ROOT = Path('/Users/andy/.openclaw/workspace')
OUT_DIR = ROOT / 'poc' / 'security'
OUT_DIR.mkdir(parents=True, exist_ok=True)
report_path = OUT_DIR / 'run_latest_report.json'

PATTERNS = {
    'AWS Access Key': re.compile(r'AKIA[0-9A-Z]{16}'),
    'Private Key': re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    'Google API Key': re.compile(r'AIza[0-9A-Za-z_-]{35}'),
    'JWT': re.compile(r'eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}'),
    'Token Assignment': re.compile(r'(?:api_key|secret|token|password)\s*[=:]\s*["\'][A-Za-z0-9_/+=-]{8,}'),
}

SKIP_DIRS = {'.git', 'node_modules', '.venv', 'venv', '__pycache__', 'credentials'}
SKIP_EXT = {'.pyc', '.png', '.jpg', '.jpeg', '.gif', '.pdf', '.zip', '.7z', '.dmg', '.ico', '.woff', '.ttf', '.db', '.sqlite', '.index'}
MAX_FILE_SIZE = 100_000

findings = []
files_scanned = 0
print('Scanning...', flush=True)

for dirpath, dirnames, filenames in os.walk(ROOT):
    dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
    for fname in filenames:
        fp = Path(dirpath) / fname
        if fp.suffix.lower() in SKIP_EXT:
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
                sev = 'CRITICAL' if name in ('AWS Access Key', 'Private Key', 'Google API Key') else 'HIGH'
                findings.append({
                    'id': len(findings) + 1,
                    'severity': sev,
                    'type': name,
                    'file': rel,
                    'line': txt[:m.start()].count('\n') + 1,
                    'match_preview': m.group(0)[:60],
                    'context': snippet[:200],
                })

now = datetime.datetime.now().isoformat()
report = {
    'generated_at': now,
    'root': str(ROOT),
    'files_scanned': files_scanned,
    'total_findings': len(findings),
    'critical': [f for f in findings if f['severity'] == 'CRITICAL'],
    'high': [f for f in findings if f['severity'] == 'HIGH'],
    'findings': findings,
}

with open(report_path, 'w', encoding='utf-8') as rf:
    json.dump(report, rf, ensure_ascii=False, indent=2)

print(f'Done. Scanned {files_scanned} files, found {len(findings)} issues.', flush=True)
print(f'Critical: {len(report["critical"])}, High: {len(report["high"])}', flush=True)
print(f'Report: {report_path}', flush=True)
