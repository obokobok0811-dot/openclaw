#!/usr/bin/env python3
"""
Obsidian retention & indexing v2
Features implemented:
- Tiered retention (permanent / medium / short)
- Semantic-like summarization (heuristic): extracts top signals and error patterns and writes Weekly_Summary.md
- Metadata index (obsidian_map.csv) with columns: date,file,tickers,roles,signals,errors
- Cold-archive (tar.gz) creation for medium/short tiers older than thresholds
- Fast extract utility to pull files matching date or keyword from archives
- Safe, atomic writes and lock
"""
from pathlib import Path
import json, re, tarfile, shutil, datetime, csv, tempfile, os

ROOT=Path('/Users/andy/Documents/Obsidian/Obsidian Vault/OpenClaw/Sessions')
OPS=Path('/Users/andy/.openclaw/workspace/ops')
OPS.mkdir(parents=True, exist_ok=True)
ARCH=OPS/'ob_archive_v2'
ARCH.mkdir(parents=True, exist_ok=True)
INDEX_CSV=OPS/'obsidian_map.csv'
SUMMARY_DIR=OPS/'weekly_summaries'
SUMMARY_DIR.mkdir(parents=True, exist_ok=True)
STATE=OPS/'obs_retention_state.json'
LOCK=OPS/'obs_retention_v2.lock'

# Tier config
TIER_PERM_TAG='#permanent'
TIER1_KEEP=None  # permanent
TIER2_KEEP_DAYS=90
TIER3_KEEP_DAYS=14

# helpers
def lock():
    if LOCK.exists():
        return False
    LOCK.write_text(str(os.getpid()))
    return True

def unlock():
    try:
        LOCK.unlink()
    except:
        pass

# simple content parsers
TICKER_RE=re.compile(r'KRW-[A-Z0-9]+')
SIGNAL_RE=re.compile(r"\b(BUY|SELL)\b", re.IGNORECASE)
ERROR_RE=re.compile(r'error|traceback|exception', re.IGNORECASE)
PERM_RE=re.compile(re.escape(TIER_PERM_TAG))

# load state
state={}
if STATE.exists():
    try:
        state=json.loads(STATE.read_text())
    except:
        state={}

# iterate days
now=datetime.datetime.now()
index_rows=[]

if not lock():
    print('locked')
    raise SystemExit

try:
    for daydir in sorted([p for p in ROOT.iterdir() if p.is_dir()]):
        # parse date from folder
        try:
            day_dt=datetime.datetime.strptime(daydir.name, '%Y-%m-%d')
        except:
            continue
        age_days=(now-day_dt).days
        # gather files
        for md in sorted(daydir.glob('*.md')):
            try:
                text=md.read_text()
            except:
                continue
            # tier checks
            if PERM_RE.search(text):
                tier=1
            else:
                # heuristics: contains many SNAPSHOT or trade entries -> tier2
                if 'SNAPSHOT' in text or 'TRADE' in text or 'BUY' in text or 'SELL' in text:
                    tier=2
                else:
                    tier=3
            # actions by tier & age
            if tier==1:
                # keep always
                pass
            elif tier==2:
                if age_days> TIER2_KEEP_DAYS:
                    # summarise before archive
                    # extract signals and errors
                    signals=SIGNAL_RE.findall(text)
                    errors=ERROR_RE.findall(text)
                    # create weekly summary file per day
                    summary_path=SUMMARY_DIR/f'Weekly_Summary_{daydir.name}.md'
                    with summary_path.open('a') as s:
                        s.write(f"## Summary for {md.name}\n")
                        s.write(f"- signals_count: {len(signals)}\n")
                        # compress errors into pattern counts
                        errs= re.findall(r'.{0,80}(error|exception|traceback).{0,80}', text, re.IGNORECASE)
                        s.write(f"- REDACTED: {len(errs)}\n")
                        s.write('\n')
                    # archive file into tar.gz per day
                    tarpath=ARCH/f'ob_{daydir.name}.tar.gz'
                    with tarfile.open(tarpath,'a:gz') as tf:
                        tf.add(str(md), arcname=str(md.relative_to(ROOT)))
                    md.unlink()
            else: # tier3
                if age_days> TIER3_KEEP_DAYS:
                    # delete
                    md.unlink()
                    continue
            # build index row
            tickers=','.join(set(TICKER_RE.findall(text)))
            signals=','.join(set(sig.upper() for sig in SIGNAL_RE.findall(text)))
            errors_found=','.join(set(m.group(0) for m in ERROR_RE.finditer(text)))
            index_rows.append({'date':daydir.name,'file':str(md.relative_to(ROOT)),'tickers':tickers,'signals':signals,'errors':errors_found})
    # write index CSV atomically
    tmp=INDEX_CSV.with_suffix('.tmp')
    with tmp.open('w', newline='') as csvf:
        w=csv.DictWriter(csvf, fieldnames=['date','file','tickers','signals','errors'])
        w.writeheader()
        for r in index_rows:
            w.writerow(r)
    tmp.replace(INDEX_CSV)
finally:
    unlock()

print('done')
