#!/usr/bin/env python3
"""run_final_check.py
Usage: python run_final_check.py
Environment:
  SIMULATED=1  # treat trades as simulated

This script fetches historical price data for KRX tickers using FinanceDataReader (fdr),
computes simple MDD and a q3_days proxy (consecutive days where ema5 < ema20 and price decreasing),
and prints RESULT_SUMMARY for each target.
"""
import os
import json
from datetime import timedelta
import pandas as pd

# targets: KRX tickers (string codes)
targets = ['005930', '000660', '005380', '068270', '035720']

# params
lookback_days = int(os.environ.get('LOOKBACK_DAYS', '365'))
end_date = pd.Timestamp.today()
start_date = end_date - pd.Timedelta(days=lookback_days)

try:
    import FinanceDataReader as fdr
except Exception as e:
    raise SystemExit('FinanceDataReader not installed. pip install finance-datareader')


def calc_mdd(series):
    roll_max = series.cummax()
    drawdown = (series - roll_max) / roll_max
    return float(drawdown.min() * 100)


def calc_q3_days(df):
    # proxy: count of days where ema5 < ema20 and price < previous price (short-term down + cross)
    df['ema5'] = df['Close'].ewm(span=5, adjust=False).mean()
    df['ema20'] = df['Close'].ewm(span=20, adjust=False).mean()
    df['price_down'] = df['Close'] < df['Close'].shift(1)
    cond = (df['ema5'] < df['ema20']) & (df['price_down'])
    # run-length of cond true days (we report total days where cond true)
    return int(cond.sum())


if __name__ == '__main__':
    result = {}
    for t in targets:
        try:
            df = fdr.DataReader(t, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
            if df.empty:
                result[t] = {'error': 'no data'}
                continue
            mdd = calc_mdd(df['Close'])
            q3 = calc_q3_days(df)
            result[t] = {'mdd': mdd, 'q3_days': q3}
        except Exception as e:
            result[t] = {'error': str(e)}
    print('RESULT_SUMMARY')
    print(json.dumps(result, indent=2))
