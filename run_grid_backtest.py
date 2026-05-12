#!/usr/bin/env python3
"""
Grid backtest runner (single-process, rate-limited)
- Fetches Upbit candle data sequentially with delay >= 0.2s
- Runs grid search over TP/SL, RSI buy threshold, EMA spans for 1m and 60m
- Saves raw data and results under workspace/backtest/
"""
import time, os, json, math
from datetime import datetime, timedelta
from pathlib import Path
import urllib.request

WORK = Path('/Users/andy/.openclaw/workspace')
OUT = WORK / 'backtest'
OUT.mkdir(parents=True, exist_ok=True)

UPBIT_TICKER = 'KRW-BTC'

# parameters
DAYS = 30
TIMEFRAMES = {'1m': 1, '60m': 60}
SLEEP = 0.25  # >=0.2s as required

# grid
TP_VALUES = [0.01, 0.02, 0.03, 0.05]
SL_VALUES = [-0.01, -0.02, -0.03, -0.05]
RSI_BUY = [25, 30, 35, 40]
EMA_SPANS = [5, 10, 20]

# helper: fetch candles sequentially (Upbit API, pages of max 200)

def fetch_candles(minutes, days):
    # need count = days * 24 * (60/minutes)
    total = int(days * 24 * (60 / minutes))
    per_page = 200
    all_candles = []
    to_iso = None
    fetched = 0
    while fetched < total:
        need = min(per_page, total - fetched)
        url = f"https://api.upbit.com/v1/candles/minutes/{minutes}?market={UPBIT_TICKER}&count={need}"
        if to_iso:
            url += f"&to={to_iso}"
        req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'})
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read().decode())
                if not data:
                    break
                # API returns newest first
                all_candles = data + all_candles
                fetched += len(data)
                to_iso = data[-1]['REDACTED']
        except Exception as e:
            print('fetch error', e)
            time.sleep(1)
            continue
        time.sleep(SLEEP)
    return all_candles

# helpers for indicators

def sma(prices, n):
    if len(prices) < n: return None
    return sum(prices[-n:]) / n


def compute_rsi(prices, period=14):
    if len(prices) < period + 1:
        return None
    gains = 0.0
    losses = 0.0
    for i in range(1, period+1):
        d = prices[-i] - prices[-i-1]
        if d>0: gains += d
        else: losses += -d
    if losses == 0:
        return 100.0
    rs = (gains/period) / (losses/period)
    return 100 - (100 / (1 + rs))

# simple backtest: entry when RSI <= rsi_buy and rising from prev, exit when pnl >= tp or pnl <= sl

def run_backtest(prices, tp, sl, rsi_buy, ema_span):
    cash = 1000000.0
    pos = 0.0
    entry_price = None
    trades = []
    prices_close = prices
    for i in range(len(prices_close)):
        if i < max(ema_span, 15):
            continue
        window = prices_close[:i+1]
        rsi_now = compute_rsi(window)
        rsi_prev = compute_rsi(window[:-1]) if len(window)>1 else None
        ema_now = sma(window, ema_span)
        price = prices_close[i]
        # entry
        if pos == 0:
            if rsi_now is not None and rsi_prev is not None and rsi_prev <= rsi_buy and rsi_now > rsi_prev:
                # buy full allocation 10% of equity
                amount = cash * 0.1
                qty = amount / price
                pos = qty
                cash -= amount
                entry_price = price
                trades.append({'side':'BUY','price':price,'qty':qty})
        else:
            pnl = (price - entry_price) / entry_price
            if pnl >= tp or pnl <= sl:
                # sell all
                cash += pos * price
                trades.append({'side':'SELL','price':price,'qty':pos,'pnl':pnl})
                pos = 0
                entry_price = None
    # final close
    if pos>0:
        cash += pos * prices_close[-1]
        pos = 0
    profit = cash - 1000000.0
    wins = sum(1 for t in trades if t.get('side')=='SELL' and t.get('pnl',0)>0)
    losses = sum(1 for t in trades if t.get('side')=='SELL' and t.get('pnl',0)<=0)
    trades_count = sum(1 for t in trades if t.get('side')=='SELL')
    win_rate = wins / trades_count if trades_count>0 else 0
    # approximate max drawdown not computed precisely here
    return {'profit':profit,'trades':trades_count,'win_rate':win_rate,'trades_detail':trades}


def main():
    results = {}
    for tf_name, minutes in TIMEFRAMES.items():
        print('Fetching', tf_name)
        candles = fetch_candles(minutes, DAYS)
        # extract close prices
        closes = [c['trade_price'] for c in candles]
        # save raw
        with open(OUT / f'closes_{tf_name}.json','w') as f:
            json.dump(closes, f)
        results[tf_name] = []
        # grid
        for tp in TP_VALUES:
            for sl in SL_VALUES:
                for rsi in RSI_BUY:
                    for ema in EMA_SPANS:
                        out = run_backtest(closes, tp, sl, rsi, ema)
                        summary = {'tp':tp,'sl':sl,'rsi_buy':rsi,'ema':ema,'profit':out['profit'],'trades':out['trades'],'win_rate':out['win_rate']}
                        results[tf_name].append(summary)
                        # write intermediate
                        with open(OUT / f'results_{tf_name}.json','w') as f:
                            json.dump(results, f)
        print('Done grid for', tf_name)
    with open(OUT / 'final_results.json','w') as f:
        json.dump(results, f)
    print('Backtest complete. Results at', OUT)

if __name__=='__main__':
    main()
