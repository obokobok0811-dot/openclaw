#!/usr/bin/env bash
set -euo pipefail
WORKDIR="$HOME/OpenClaw"

# 1) create venv if missing
if [ ! -d "venv" ]; then
  python3 -m venv venv
fi
# activate
# shellcheck disable=SC1091
source venv/bin/activate

# 1b) install required packages (use --upgrade pip first)
python3 -m pip install --upgrade pip
python3 -m pip install finance-datareader yfinance pandas matplotlib ta || {
  echo "Package install failed; try installing ta with system deps or use 'ta' replacement." >&2
}

# 2) write run_stress_test.py
cat > "$WORKDIR/run_stress_test.py" <<'PY'
#!/usr/bin/env python3
import FinanceDataReader as fdr
import pandas as pd, numpy as np
from pathlib import Path
from datetime import datetime

OUT = Path('/Users/andy/.openclaw/workspace/data')
OUT.mkdir(parents=True, exist_ok=True)

# 1) load 2016-01-01..2026-05-09 for 005930
start='2016-01-01'; end='2026-05-09'
sym='005930'
print('FETCHING', sym)
df = fdr.DataReader(sym, start, end)
df.to_csv(OUT / f"{sym}_fdr.csv")
df.index = pd.to_datetime(df.index)
df = df.sort_index()  # chronological

# compute indicators: SMA20, SMA60, ATR(14), ATR20_mean (rolling mean of ATR)
df['sma20'] = df['Close'].rolling(20).mean()
df['sma60'] = df['Close'].rolling(60).mean()
# True Range and ATR14
df['tr'] = pd.concat([
    df['High'] - df['Low'],
    (df['High'] - df['Close'].shift(1)).abs(),
    (df['Low'] - df['Close'].shift(1)).abs()
], axis=1).max(axis=1)
df['atr14'] = df['tr'].rolling(14).mean()
df['atr20_mean'] = df['atr14'].rolling(20).mean()

# helper functions
def quadrant_row(r):
    if pd.isna(r['sma60']) or pd.isna(r['atr14']) or pd.isna(r['atr20_mean']):
        return None
    trend_up = r['Close'] > r['sma60']
    vol_high = r['atr14'] > r['atr20_mean']
    if trend_up and not vol_high:
        return 1
    if trend_up and vol_high:
        return 2
    if (not trend_up) and not vol_high:
        return 3
    return 4

[df.__setitem__('quadrant', df.apply(quadrant_row, axis=1))]

# compute RSI for use in buy rule
delta = df['Close'].diff()
gain = delta.clip(lower=0)
loss = -delta.clip(upper=0)
df['avg_gain'] = gain.rolling(14).mean()
df['avg_loss'] = loss.rolling(14).mean()
rs = df['avg_gain'] / df['avg_loss'].replace(0, np.nan)
df['rsi14'] = 100 - (100/(1+rs))

# buyA rule
.df = df.copy()
.df['buyA'] = (.df['Close'] > .df['sma60']) & (.df['Close'] < .df['sma20']) & (.df['rsi14'] <= 40)

# next return for weapon B naive hit test
.df['next_ret'] = .df['Close'].shift(-1) / .df['Open'] - 1
.threshold_ret = 0.03
.df['weaponB_hit'] = (.df['quadrant'] == 4) & (.df['next_ret'] >= _threshold_ret)

# MDD compute
def compute_mdd(equity_curve):
    peak = -1e18
    mdd = 0.0
    for v in equity_curve:
        if v>peak: peak=v
        dd = (peak - v)/peak*100 if peak>0 else 0
        if dd>mdd: mdd=dd
    return mdd

# simulate naive equity from buyA signals: start equity 1_000_000

def simulate_window(start_date, end_date):
    sub = .df[(.df.index >= start_date) & (.df.index <= end_date)].copy()
    if sub.empty:
        return {'days':0}
    counts = sub['quadrant'].value_counts().to_dict()
    # buys in quadrant3
    buys_in_q3 = int(sub[(sub['quadrant']==3) & (sub['buyA'])].shape[0])
    total_q3 = counts.get(3,0)
    chaos_hits = int(sub['weaponB_hit'].sum())
    chaos_days = int((sub['quadrant']==4).sum())
    # simulate equity
    equity = 1_000_000.0
    equity_curve = []
    pos = 0
    entry_price = 0
    for idx,row in sub.iterrows():
        if row['buyA'] and pos==0:
            pos = 1
            entry_price = row['Close']
        if pos==1:
            equity = equity + (row['Close'] - entry_price)
        equity_curve.append(equity)
    mdd = compute_mdd(equity_curve) if equity_curve else 0.0
    return {'days':len(sub), 'counts':counts, 'mdd_pct':round(mdd,2), 'buys_in_q3':buys_in_q3, 'q3_days':total_q3, 'chaos_hits':chaos_hits, 'chaos_days':chaos_days}

res1 = simulate_window('2020-02-01','2020-04-30')
res2 = simulate_window('2022-07-01','2022-12-31')

print('RESULT_SUMMARY')
print('window1', res1)
print('window2', res2)
PY

# 3) run the test and display
python3 "$WORKDIR/run_stress_test.py" | sed -n '1,200p'
