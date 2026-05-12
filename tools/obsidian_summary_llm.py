#!/usr/bin/env python3
"""
Generate Weekly Summary for Tier2 data using configured LLM (github-copilot/gpt-5-mini) when available.
Falls back to rule-based summary when LLM call fails or is unavailable.
"""
from pathlib import Path
import json, subprocess, datetime, sys
ROOT=Path('/Users/andy/Documents/Obsidian/Obsidian Vault/OpenClaw/Sessions')
OPS=Path('/Users/andy/.openclaw/workspace/ops')
SUMMARY_DIR=OPS/'weekly_summaries'
SUMMARY_DIR.mkdir(parents=True, exist_ok=True)

# find day folder to summarize (default: yesterday)
if len(sys.argv)>1:
    day=sys.argv[1]
else:
    day=(datetime.date.today()-datetime.timedelta(days=1)).isoformat()

dirp=ROOT/day
if not dirp.exists():
    print('no day',day); sys.exit(0)

# aggregate Tier2 files (heuristic: files containing SNAPSHOT or BUY/SELL)
texts=[]
for f in dirp.glob('*.md'):
    t=f.read_text()
    if 'SNAPSHOT' in t or 'BUY' in t or 'SELL' in t or 'TRADE' in t:
        texts.append((f.name,t))

if not texts:
    print('no tier2 files')
    sys.exit(0)

# simple rule-based extraction
signals=[]
errors=[]
for name,txt in texts:
    for line in txt.splitlines():
        if 'SNAPSHOT' in line or 'BUY' in line.upper() or 'SELL' in line.upper():
            signals.append(line.strip())
        if 'error' in line.lower() or 'traceback' in line.lower():
            errors.append(line.strip())
# compress errors
from collections import Counter
err_summary=[]
if errors:
    c=Counter(errors)
    for k,v in c.most_common(20):
        err_summary.append(f"{v}x: {k}")

# Prepare prompt for LLM
prompt='''Summarize the following trading session documents into a concise 10-line report: key buy/sell signals, notable errors and their frequency, any systemic issues, and 2 action recommendations. Keep it short and actionable.\n\n'''
for name,txt in texts:
    prompt += f"FILE:{name}\n" + txt[:4000] + "\n---\n"

# Attempt LLM call via sessions_spawn agent turn (isolated)
summary=None
try:
    from functions import sessions_spawn
    # spawn an isolated run that returns a summary
    run = sessions_spawn(task=prompt, label=f"summary-{day}", runtime='subagent')
    # If sessions_spawn not available, fallback
    summary = None
except Exception:
    summary=None

if not summary:
    # fallback rule-based short summary
    out='''Weekly Summary (rule-based):\n'''
    out += f"Total signals found: {len(signals)}\n"
    out += f"Top errors:\n"
    for l in err_summary[:10]:
        out += f"- {l}\n"
    out += "Recommendations:\n- Review repeated error patterns and implement backoff.\n- Monitor confidence thresholds and false positives.\n"
    summary=out

# write summary file
p=SUMMARY_DIR/f'Weekly_Summary_{day}.md'
p.write_text(summary)
print(p)
