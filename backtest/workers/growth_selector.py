#!/usr/bin/env python3
"""
Find future-growth top3 selector for KOSPI100 universe.
Creates markdown reports under Stock_Study.
"""
import os, json, math, statistics, datetime
from collections import deque

VAULT = '/Users/andy/Documents/Obsidian/Openclaw_Notes/Stock_Study'
os.makedirs(VAULT, exist_ok=True)

# utility funcs
def sma(series, window):
    if len(series) < window:
        return None
    return sum(series[-window:]) / window

def rsi(series, window=14):
    # series: list of closes
    if len(series) < window+1:
        return None
    gains = 0.0; losses = 0.0
    for i in range(-window,0):
        diff = series[i] - series[i-1]
        if diff>0: gains += diff
        else: losses -= diff
    if gains+losses == 0:
        return 50.0
    rs = (gains / window) / (losses / window) if losses!=0 else float('inf')
    if rs==float('inf'):
        return 100.0
    return 100.0 - (100.0 / (1.0 + rs))

def pct_diff(a,b):
    try:
        return (a-b)/b
    except Exception:
        return None

# main algorithm
def evaluate_ticker(history):
    # history: dict with 'index' (timestamps) and 'data' list of rows [O,H,L,C,V]
    closes = [row[3] for row in history.get('data',[])]
    vols = [row[4] for row in history.get('data',[])]
    if len(closes) < 60:
        return None
    cur = closes[-1]
    ma20 = sma(closes,20)
    ma60 = sma(closes,60)
    ma120 = sma(closes,120)
    rsi14 = rsi(closes,14)
    # condition A
    if rsi14 is None or rsi14 >= 70:
        return None
    # condition B: proximity to 20MA or 60MA within ±5%
    prox20 = abs(cur - ma20)/ma20 if ma20 else 1.0
    prox60 = abs(cur - ma60)/ma60 if ma60 else 1.0
    # allow ±8% proximity
    near_support = (prox20 <= 0.08) or (prox60 <= 0.08)
    if not near_support:
        return None
    # condition C: volume analysis
    # define last 10 periods as recent days; separate up days vs down days
    recent = list(zip(closes[-30:], vols[-30:]))
    down_days_vols = [v for (c,v),(c_prev,_) in zip(recent[1:], recent[:-1]) if c < c_prev]
    up_days_vols = [v for (c,v),(c_prev,_) in zip(recent[1:], recent[:-1]) if c >= c_prev]
    # be conservative: require mean(down_days_vols) <= mean(up_days_vols) * 1.0
    if len(up_days_vols)==0:
        return None
    mean_down = statistics.mean(down_days_vols) if down_days_vols else 0
    mean_up = statistics.mean(up_days_vols)
    if mean_down > mean_up * 0.9:
        # if down-day volume is not materially lower, suspect distribution; reject
        return None
    # score by proximity to nearer of ma20/ma60 (lower is better)
    proximity = min(prox20 if ma20 else 1.0, prox60 if ma60 else 1.0)
    return {
        'current': cur,
        'ma20': ma20,
        'ma60': ma60,
        'ma120': ma120,
        'rsi14': rsi14,
        'proximity': proximity,
        'mean_down_vol': mean_down,
        'mean_up_vol': mean_up
    }

def REDACTED(source_path, universe_tickers=None):
    # source_path: JSON file mapping ticker -> history dict
    with open(source_path,'r') as f:
        data = json.load(f)
    # determine 6-month returns for universe; assume index has ISO dates increasing
    returns = []
    for t,h in data.items():
        # skip if not in provided universe_tickers
        if universe_tickers and t not in universe_tickers:
            continue
        try:
            closes = [row[3] for row in h.get('data',[])]
            if len(closes) < 120:
                continue
            # approx 6 months as 120 trading days
            ret = (closes[-1] / closes[-120]) - 1.0
            returns.append((t, ret))
        except Exception:
            continue
    # pick top 30
    top5 = [t for t,_ in sorted(returns, key=lambda x: x[1], reverse=True)[:30]]
    candidates = []
    for t in top5:
        res = evaluate_ticker(data[t])
        if res:
            candidates.append((t,res))
    # sort by proximity (ascending)
    candidates_sorted = sorted(candidates, key=lambda x: x[1]['proximity'])
    top3 = candidates_sorted[:3]
    return top3

def write_report(selected):
    # selected: list of (ticker, metrics)
    date = datetime.date.today().strftime('%Y%m%d')
    lines = []
    for t, m in selected:
        name = t
        cur = m['current']
        prox20 = (cur - m['ma20'])/m['ma20'] if m['ma20'] else None
        rsi14 = m['rsi14']
        reason = f"Near support (proximity {m['proximity']:.3f}), RSI {rsi14:.1f}, down-vol {m['mean_down_vol']:.0f} vs up-vol {m['mean_up_vol']:.0f}"
        mdname = os.path.join(VAULT, f"{t}_{date}.md")
        with open(mdname,'w') as f:
            f.write(f"# {t} FUTURE GROWTH CANDIDATE {date}\n")
            f.write(f"- current: {cur}\n")
            f.write(f"- 20MA_diff: {prox20:.4f}\n")
            f.write(f"- RSI14: {rsi14:.1f}\n")
            f.write('\n')
            f.write('## Reason for selection\n')
            f.write(reason + "\n")
        lines.append(mdname)
    return lines

if __name__ == '__main__':
    # try common data paths
    candidates = []
    for path in ['/Users/andy/.openclaw/workspace/backtest/closes_daily.json', '/Users/andy/.openclaw/workspace/backtest/closes_1m.json']:
        if os.path.exists(path):
            selected = REDACTED(path)
            if selected:
                out = write_report(selected)
                print('wrote', out)
                break
    else:
        print('no data file found')
