import FinanceDataReader as fdr
import pandas as pd
from ta.trend import SMAIndicator
from ta.volatility import AverageTrueRange

def get_report(start, end):
    df = fdr.DataReader('005930', start, end).sort_index()
    df['SMA60'] = SMAIndicator(df['Close'], window=60).sma_indicator()
    df['ATR'] = AverageTrueRange(df['High'], df['Low'], df['Close'], window=14).average_true_range()
    df['ATR_avg'] = df['ATR'].rolling(20).mean()
    df['q'] = 0
    df.loc[(df['Close']>df['SMA60'])&(df['ATR']<df['ATR_avg']), 'q'] = 1
    df.loc[(df['Close']>df['SMA60'])&(df['ATR']>=df['ATR_avg']), 'q'] = 2
    df.loc[(df['Close']<=df['SMA60'])&(df['ATR']<df['ATR_avg']), 'q'] = 3
    df.loc[(df['Close']<=df['SMA60'])&(df['ATR']>=df['ATR_avg']), 'q'] = 4
    
    df['Ret'] = df['Close'].pct_change().fillna(0)
    df['Cum'] = (1+df['Ret']).cumprod()
    mdd = ((df['Cum']/df['Cum'].cummax())-1).min() * 100
    q3_buys = int((df['q']==3).sum())
    return {'mdd': round(mdd,2), 'q3_days': q3_buys}

print("RESULT_SUMMARY")
print("window1 (2020):", get_report('2020-02-01','2020-04-30'))
print("window2 (2022):", get_report('2022-07-01','2022-12-31'))
