#!/usr/bin/env python3
import os, re, json, datetime
from pathlib import Path

ROOT=Path('/Users/andy/.openclaw/workspace')
OUT_DIR=ROOT / 'poc' / 'security'
OUT_DIR.mkdir(parents=True, exist_ok=True)
report_path=OUT_DIR / 'run_latest_report.json'
log_path=OUT_DIR / 'run_latest.log'

# patterns for quick offensive/privacy checks
PATTERNS={
    'AWS Access Key': re.compile(r'AKIA[0-9A-Z]{16}'),
    'Private Key Begin': re.compile(r'-----BEGIN (RSA|EC|OPENSSH|PRIVATE) KEY-----'),
    'Google API Key-like': re.compile(r'AIza[0-9A-Za-z\-_]{35}'),
    'JWT-looking': re.compile(r'eyJ[0-9A-Za-z\-_]{10,}\.[0-9A-Za-z\-_]{10,}\.[0-9A-Za-z\-_]{10,}'),
    'Generic token': re.compile(r'(?i)(?:api[_-]?key|secret|token|passwd|password)["\']?\s*[:=]\s*["\']?[A-Za-z0-9\-_=/.+]{8,}'),
}

exclusions=['.git', 'node_modules', 'venv', '.venv', 'poc/security', 'credentials']

findings=[]
start=datetime.datetime.utcnow().isoformat()+ 'Z'
with open(log_path,'w',encoding='utf-8') as logf:
    logf.write(f'Scan started: {start}\n')
    for dirpath, dirnames, filenames in os.walk(ROOT):
        # skip excluded dirs
        parts=Path(dirpath).parts
        if any(ex in parts for ex in exclusions):
            continue
        for fname in filenames:
            fp=Path(dirpath)/fname
            try:
                # skip large files
                if fp.stat().st_size>200_000: continue
                txt=fp.read_text(errors='ignore')
            except Exception as e:
                logf.write(f'WARN reading {fp}: {e}\n')
                continue
            for name,pat in PATTERNS.items():
                for m in pat.finditer(txt):
                    snippet=txt[max(0,m.start()-40):m.end()+40].replace('\n',' ')
                    finding={
                        'id': f'{fp}:{m.start()}',
                        'severity': 'CRITICAL' if name in ('AWS Access Key','Private Key Begin','Google API Key-like') else 'HIGH',
                        'title': name,
                        'file': str(fp.relative_to(ROOT)),
                        'match': m.group(0)[:200],
                        'snippet': snippet[:400]
                    }
                    findings.append(finding)
                    logf.write(f'FIND {finding["severity"]} {finding["title"]} in {finding["file"]}\n')

end=datetime.datetime.utcnow().isoformat()+ 'Z'
report={'generated_at':end,'root':str(ROOT),'findings':findings}
with open(report_path,'w',encoding='utf-8') as rf:
    json.dump(report,rf,ensure_ascii=False,indent=2)
with open(log_path,'a',encoding='utf-8') as logf:
    logf.write(f'Scan finished: {end}, findings: {len(findings)}\n')
print('scan complete, findings=',len(findings))
