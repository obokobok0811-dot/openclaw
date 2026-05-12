#!/usr/bin/env python3
"""Weapon A - value/swing module for BULL regime.
Entry: call run_weapon_a()

Behavior:
 - targets: ['005930','005380','003490','035420','000660']
 - tries KIS daily-price API first (inquire-daily-price, tr_id FHKST01010400)
 - on API failure falls back to local CSV under ./data/<symbol>.csv (created by data_io.append_price_csv)
 - computes SMA20, SMA60, RSI14 from chronological closes and evaluates buy/sell signals per spec.
 - does not place live orders; returns a report dict describing signals for each symbol.
"""

import os, time, requests, math, csv
from pathlib import Path
from statistics import mean

SYMBOLS = ['005930','005380','003490','035420','000660']
BASE = 'https://openapivts.koreainvestment.com:29443'
TOKEN_URL = BASE + '/oauth2/token'
API_DAILY = '/uapi/domestic-stock/v1/quotations/inquire-daily-price'
TR_ID = 'FHKST01010400'

# helper indicators
def sma(arr, n):
    if len(arr) < n: return None
    return sum(arr[-n:]) / n

def rsi_series(prices, period=14):
    if len(prices) < period+1: return [None]*len(prices)
    deltas = [prices[i] - prices[i-1] for i in range(1,len(prices))]
    gains = [d if d>0 else 0 for d in deltas]
    losses = [-d if d<0 else 0 for d in deltas]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    rs_vals = [None]*(period)
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain*(period-1) + gains[i]) / period
        avg_loss = (avg_loss*(period-1) + losses[i]) / period
        if avg_loss == 0:
            rs_vals.append(100.0)
        else:
            rs = avg_gain / avg_loss
            rs_vals.append(100 - (100/(1+rs)))
    return [None] + rs_vals  # align length

# try get token from .env.kis
def REDACTED():
    env_path = Path(__file__).parent / '.env.kis'
    if not env_path.exists():
        return None
    with open(env_path) as f:
        for line in f:
            if '=' in line:
                k,v=line.strip().split('=',1)
                os.environ[k]=v.strip('"')
    appkey = os.getenv('KIS_APP_KEY')
    appsecret = os.getenv('KIS_APP_SECRET')
    if not (appkey and appsecret):
        return None
    try:
        resp = requests.post(TOKEN_URL, data={'grant_type':'client_credentials','appkey':appkey,'appsecret':appsecret}, timeout=10)
        resp.raise_for_status()
        token = resp.json().get('access_token')
        headers = {'appkey':appkey,'appsecret':appsecret,'Authorization':'Bearer '+token,'Content-Type':'application/json; charset=utf-8','tr_id':TR_ID}
        return headers
    except Exception:
        return None

# fetch daily via API (no date params to get recent chunk)
def fetch_daily_api(symbol, headers, limit=200):
    params = {'REDACTED':'J','FID_INPUT_ISCD':symbol,'FID_PERIOD_DIV_CODE':'D','FID_ORG_ADJ_PRC':'0','FID_INPUT_HOUR':'100'}
    try:
        r = requests.get(BASE + API_DAILY, params=params, headers=headers, timeout=15)
        if r.status_code != 200:
            return None
        j = r.json()
        arr = j.get('output2') or j.get('output1') or j.get('output')
        if isinstance(arr, dict):
            for v in arr.values():
                if isinstance(v, list):
                    arr = v; break
        if not arr:
            return None
        closes = []
        dates = []
        for item in arr[:limit]:
            if isinstance(item, dict):
                d = item.get('stck_bsop_date') or item.get('date')
                c = item.get('stck_clpr') or item.get('stck_prpr') or item.get('close')
                if d and c is not None:
                    try:
                        closes.append(float(c)); dates.append(d)
                    except:
                        continue
        # API often returns newest-first; reverse to chronological
        if len(closes) and dates:
            closes = list(reversed(closes))
            dates = list(reversed(dates))
        return {'dates': dates, 'closes': closes}
    except Exception:
        return None

# fallback CSV loader
def fetch_daily_csv(symbol):
    p = Path(__file__).parent / 'data' / f"{symbol}.csv"
    if not p.exists():
        return None
    closes = []
    dates = []
    try:
        with p.open() as f:
            reader = csv.DictReader(f)
            for row in reader:
                d = row.get('date')
                c = row.get('close')
                if d and c:
                    try:
                        closes.append(float(c)); dates.append(d)
                    except:
                        continue
        return {'dates': dates, 'closes': closes}
    except Exception:
        return None

# main entry
def rank_scale(scores):
    # scores: dict sym->score (float). return dict sym->0..1 rank scaling
    items = [(s,v) for s,v in scores.items()]
    vals = [v for _,v in items]
    if not vals:
        return {s:0.0 for s in scores}
    minv = min(vals); maxv = max(vals)
    if maxv == minv:
        return {s:0.5 for s in scores}
    out = {}
    for s,v in items:
        out[s] = (v - minv)/(maxv - minv)
    return out


def REDACTED(symbol):
    # delta(volume,1) >0 and delta(close,1) <0 on last day
    p = Path(__file__).parent / 'data' / f"{symbol}.csv"
    if not p.exists():
        return None
    try:
        with p.open() as fh:
            reader = list(csv.DictReader(fh))
            if len(reader) < 2:
                return None
            last = reader[-1]
            prev = reader[-2]
            vol_last = int(last.get('volume') or 0)
            vol_prev = int(prev.get('volume') or 0)
            close_last = float(last.get('close') or 0)
            close_prev = float(prev.get('close') or 0)
            delta_vol = vol_last - vol_prev
            delta_close = close_last - close_prev
            return {'delta_vol': delta_vol, 'delta_close': delta_close}
    except Exception:
        return None


def run_weapon_a(simulate=False):
    """Return dict of signals/results for each symbol.
    If simulate=True, no API calls attempted (use CSV only).
    Reads WEIGHT_A from env to respect allocated capital share.
    Applies Alpha#12 to increase weight by 1.5x when condition met.
    """
    results = {}
    base_weight_a = float(os.getenv('WEIGHT_A') or 0.0)
    headers = None
    if not simulate:
        headers = REDACTED()
        # respect API limits; headers may be None if token fetch failed
    # prepare alpha12 scoring map
    alpha12_scores = {}
    for sym in SYMBOLS:
        ad = REDACTED(sym)
        score = 0.0
        if ad:
            if ad['delta_vol'] > 0 and ad['delta_close'] < 0:
                score = 1.0
        alpha12_scores[sym] = score
    alpha12_rank = rank_scale(alpha12_scores)

    for sym in SYMBOLS:
        data = None
        if headers:
            data = fetch_daily_api(sym, headers)
            time.sleep(1.5)  # throttle as required
        if data is None:
            data = fetch_daily_csv(sym)
        if not data or len(data.get('closes',[])) < 60:
            results[sym] = {'status':'insufficient_data'}
            continue
        closes = data['closes']
        dates = data['dates']
        sma20 = sma(closes,20)
        sma60 = sma(closes,60)
        rsi = rsi_series(closes,14)
        current = closes[-1]
        prev = closes[-2] if len(closes)>=2 else None
        # base entry condition
        buy = False
        sell = False
        if sma60 is not None and sma20 is not None and rsi[-1] is not None:
            if current > sma60 and current < sma20 and rsi[-1] <= 40:
                buy = True
        if current >= sma20 or (rsi[-1] is not None and rsi[-1] >= 60):
            sell = True
        # adjust weight if alpha12 triggers (and rsi condition also satisfied)
        weight_a = base_weight_a
        if alpha12_rank.get(sym,0) > 0 and rsi[-1] is not None and rsi[-1] <= 40 and buy:
            weight_a = weight_a * 1.5
        results[sym] = {
            'status':'ok',
            'current': current,
            'sma20': round(sma20,2) if sma20 else None,
            'sma60': round(sma60,2) if sma60 else None,
            'rsi14': round(rsi[-1],2) if rsi[-1] else None,
            'buy_signal': buy,
            'sell_signal': sell,
            'weight': weight_a,
            'alpha12_score': alpha12_rank.get(sym,0)
        }
    return results

if __name__ == '__main__':
    import json
    out = run_weapon_a(simulate=True)
    print(json.dumps(out, ensure_ascii=False, indent=2))
