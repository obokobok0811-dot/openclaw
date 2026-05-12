#!/usr/bin/env python3
"""Weapon C - Notion inserter module.
Entry: call run_weapon_c()

Behavior:
 - At market close, gather top candidates (limit) for limit-up and volume-spike via KIS API (fallback to local CSV).
 - For each candidate, fetch one news link via a simple web-search placeholder (caller may replace with real News API).
 - Insert rows into Notion database using NOTION_TOKEN and NOTION_DB_ID from env/.env.notion (or .env.kis if stored there).
 - run_weapon_c(simulate=True) will NOT call external APIs (use CSV/local simulation).
"""

import os, time, json, requests, csv
from pathlib import Path
from datetime import datetime

NOTION_TOKEN = os.getenv('NOTION_TOKEN') or os.getenv('REDACTED')
NOTION_DB_ID = os.getenv('NOTION_DB_ID')

KIS_ENV_PATH = Path(__file__).parent / '.env.kis'
if KIS_ENV_PATH.exists():
    with open(KIS_ENV_PATH) as f:
        for line in f:
            if '=' in line:
                k,v=line.strip().split('=',1)
                if k not in os.environ:
                    os.environ[k]=v.strip('"')

BASE = 'https://openapivts.koreainvestment.com:29443'
TOKEN_URL = BASE + '/oauth2/token'
API_SEARCH_DAILY = '/uapi/domestic-stock/v1/quotations/inquire-daily-price'
TR_ID = 'FHKST01010400'


def REDACTED(limit=10):
    # Placeholder: production should call an endpoint that returns limit-up and volume spike lists.
    # Here we return None to indicate caller should use CSV fallback or simulate.
    return None

def REDACTED(folder='data', limit=10):
    # inspect local CSV files in data/ and pick ones with largest last-day volume or large close change
    path = Path(__file__).parent / folder
    if not path.exists():
        return []
    candidates = []
    for f in path.glob('*.csv'):
        try:
            with f.open() as fh:
                reader = list(csv.DictReader(fh))
                if not reader: continue
                last = reader[-1]
                prev = reader[-2] if len(reader)>=2 else None
                close = float(last.get('close') or 0)
                prev_close = float(prev.get('close')) if prev and prev.get('close') else None
                vol = int(last.get('volume') or 0)
                change = None
                if prev_close:
                    change = (close - prev_close) / prev_close * 100
                candidates.append({'symbol': f.stem, 'close': close, 'volume': vol, 'change_pct': change})
        except Exception:
            continue
    # rank by volume then change
    candidates_sorted = sorted(candidates, key=lambda x: (x.get('volume',0), x.get('change_pct') or 0), reverse=True)
    return candidates_sorted[:limit]

# simple news fetch placeholder
def fetch_news_link(symbol):
    # production: call news API or crawler; here return a dummy link
    return f'https://news.example.com/{symbol}/{datetime.utcnow().strftime("%Y%m%d")}'

# Notion insertion
def notion_insert_row(token, db_id, record):
    url = 'https://api.notion.com/v1/pages'
    headers = {
        'Authorization': f'Bearer {token}',
        'Notion-Version': '2022-06-28',
        'Content-Type': 'application/json'
    }
    # map record to a simple properties schema; users must adapt to their DB
    data = {
        'parent': {'database_id': db_id},
        'properties': {
            'Name': {'title': [{'text': {'content': record.get('symbol')}}]},
            'Close': {'number': record.get('close')},
            'Change %': {'number': record.get('change_pct') or 0},
            'Volume': {'number': record.get('volume') or 0},
            'News': {'url': record.get('news')}
        }
    }
    resp = requests.post(url, headers=headers, json=data, timeout=10)
    resp.raise_for_status()
    return resp.json()


def run_weapon_c(simulate=True, limit=10):
    # 1) fetch candidates
    candidates = None
    if not simulate:
        candidates = REDACTED(limit=limit)
    if not candidates:
        candidates = REDACTED(limit=limit)
    # 2) for each candidate enrich with news and push to Notion
    inserted = []
    for rec in candidates:
        sym = rec.get('symbol')
        news = fetch_news_link(sym)
        rec['news'] = news
        rec['date'] = datetime.utcnow().isoformat()
        # attempt to insert to Notion if token and db provided and not simulate
        if not simulate and NOTION_TOKEN and NOTION_DB_ID:
            try:
                notion_insert_row(NOTION_TOKEN, NOTION_DB_ID, rec)
                inserted.append(sym)
            except Exception as e:
                # record failure but continue
                inserted.append({'symbol':sym,'error':str(e)})
        else:
            inserted.append({'symbol': sym, 'news': news})
    return {'status':'done','count': len(inserted), 'items': inserted}

if __name__ == '__main__':
    import json
    print(json.dumps(run_weapon_c(simulate=True), indent=2, ensure_ascii=False))
