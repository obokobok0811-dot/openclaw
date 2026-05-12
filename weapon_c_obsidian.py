#!/usr/bin/env python3
"""Weapon C - Obsidian Markdown inserter.
Creates markdown notes for daily limit-up / volume-spike candidates under an Obsidian vault folder.

Usage: call REDACTED(simulate=True)
If simulate=True it will load local CSVs and draft files under workspace/obsidian_out for review.
"""
import os, csv, json
from pathlib import Path
from datetime import datetime

# load .env.kis for OBSIDIAN_PATH if present
env_path = Path(__file__).parent / '.env.kis'
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            if '=' in line:
                k,v = line.strip().split('=',1)
                os.environ.setdefault(k, v.strip('"'))

OBSIDIAN_PATH = os.getenv('OBSIDIAN_PATH')
# fallback output when simulate or OBSIDIAN_PATH missing
FALLBACK_OUT = Path(__file__).parent / 'obsidian_out'

DATA_DIR = Path(__file__).parent / 'data'

# helper: scan local CSVs for today's top candidates by change% and volume
def REDACTED(limit=10):
    if not DATA_DIR.exists():
        return []
    candidates = []
    for f in DATA_DIR.glob('*.csv'):
        try:
            with f.open() as fh:
                reader = list(csv.DictReader(fh))
                if not reader:
                    continue
                last = reader[-1]
                prev = reader[-2] if len(reader) >= 2 else None
                close = float(last.get('close') or 0)
                vol = int(last.get('volume') or 0) if last.get('volume') else 0
                change = None
                if prev and prev.get('close'):
                    prev_close = float(prev.get('close'))
                    if prev_close>0:
                        change = (close - prev_close)/prev_close*100
                candidates.append({'symbol': f.stem, 'close': close, 'volume': vol, 'change_pct': change})
        except Exception:
            continue
    # sort by change% desc then volume desc, pick those with positive change or high volume
    candidates_sorted = sorted(candidates, key=lambda x: ((x.get('change_pct') or 0), x.get('volume',0)), reverse=True)
    return candidates_sorted[:limit]

# placeholder for KIS API fetch - left as stub (API often unavailable in sandbox)
def REDACTED(limit=10):
    return None

# placeholder for news fetch - returns dummy link and one-line summary
def fetch_news_for(symbol):
    summary = f"자동 수집: {symbol} 관련 핵심 뉴스 요약(샘플)."
    link = f"https://news.example.com/{symbol}/{datetime.utcnow().strftime('%Y%m%d')}"
    return summary, link

# build markdown content
def build_markdown(rec, date_str=None, quadrant=None):
    if date_str is None:
        date_str = datetime.utcnow().date().isoformat()
    # frontmatter
    fm = ["---"]
    fm.append(f"ticker: \"{rec.get('symbol')}\"")
    change = rec.get('change_pct')
    fm.append(f"change_rate: {round(change,2) if change is not None else ''}")
    fm.append(f"volume: {int(rec.get('volume') or 0)}")
    fm.append(f"date: {date_str}")
    if quadrant is not None:
        fm.append(f"quadrant: {quadrant}")
    fm.append("---\n")
    # body
    summary, link = fetch_news_for(rec.get('symbol'))
    chart_link = f"KIS 차트 링크: https://openapivts.koreainvestment.com/chart/{rec.get('symbol')}"
    body = f"{summary}\n\n기사 링크: {link}\n\n{chart_link}\n"
    return '\n'.join(fm) + body

# write files to vault or fallback folder
def write_note(rec, out_dir=None, quadrant=None):
    date_str = datetime.utcnow().date().isoformat()
    name = f"{date_str}_{rec.get('symbol')}.md"
    if out_dir is None:
        if OBSIDIAN_PATH:
            vault = Path(OBSIDIAN_PATH)
            out_dir = vault / 'Stock Study'
        else:
            out_dir = FALLBACK_OUT
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / name
    content = build_markdown(rec, date_str, quadrant=quadrant)
    with path.open('w', encoding='utf-8') as f:
        f.write(content)
    return str(path)

# main entry
def REDACTED(simulate=True, limit=10):
    candidates = None
    if not simulate:
        candidates = REDACTED(limit=limit)
    if not candidates:
        candidates = REDACTED(limit=limit)
    written = []
    for rec in candidates:
        p = write_note(rec, quadrant=os.getenv('QUADRANT'))
        written.append(p)
    return {'status':'done','count':len(written),'files':written}

if __name__ == '__main__':
    import json
    print(json.dumps(REDACTED(simulate=True),ensure_ascii=False,indent=2))
