#!/usr/bin/env python3
import os, time, requests, math, json
from pathlib import Path

# load .env.kis
env_path = Path(__file__).parent / '.env.kis'
if not env_path.exists():
    raise SystemExit('Missing .env.kis')
with open(env_path) as f:
    for line in f:
        if '=' in line:
            k,v=line.strip().split('=',1)
            os.environ[k]=v.strip('"')

APP_KEY=os.getenv('KIS_APP_KEY')
APP_SECRET=os.getenv('KIS_APP_SECRET')
if not (APP_KEY and APP_SECRET):
    raise SystemExit('Missing keys')

TOKEN_URL='https://openapivts.koreainvestment.com:29443/oauth2/token'
resp=requests.post(TOKEN_URL,data={'grant_type':'client_credentials','appkey':APP_KEY,'appsecret':APP_SECRET},timeout=10)
resp.raise_for_status()
token=resp.json().get('access_token')
headers_base={'appkey':APP_KEY,'appsecret':APP_SECRET,'Authorization':'Bearer '+token,'Content-Type':'application/json; charset=utf-8'}
base='https://openapivts.koreainvestment.com:29443'

symbols = [('005930','삼성전자'),('005380','현대차'),('003490','대한항공'),('035420','NAVER'),('000660','SK하이닉스')]
results = {}

# backtest params
initial_cap = 10_000_000.0
fee_pct = 0.0015 # 0.15%
slippage_pct = 0.0015

for code,name in symbols:
    time.sleep(1.5)
    # paging: API returns max 30 per call. loop until we have ~250 days
    collected = []
    params = {'REDACTED':'J','FID_INPUT_ISCD':code,'FID_PERIOD_DIV_CODE':'D','FID_ORG_ADJ_PRC':'0','FID_INPUT_HOUR':'30'}
    headers = {**headers_base,'tr_id':'FHKST01010400'}
    while len(collected) < 250:
        time.sleep(1.5)
        r=requests.get(base + '/uapi/domestic-stock/v1/quotations/inquire-daily-price', params=params, headers=headers, timeout=30)
        if r.status_code!=200:
            print('ERR',code,r.status_code,r.text[:200])
            break
        j=r.json()
        arr = j.get('output') or j.get('output1') or j.get('output2')
        if not arr:
            print('ERR no chunk',code)
            break
        # append chunk (arr[0] is latest of chunk)
        collected.extend(arr)
        # determine next end date: take last element's date and request earlier than that
        last_date = arr[-1].get('stck_bsop_date')
        if not last_date:
            break
        # set next param to fetch prior days - API may use FID_INPUT_DATE to set end date
        params['FID_INPUT_DATE'] = last_date
        # safety: if chunk size <30 then likely no more data
        if len(arr) < 30:
            break
    if len(collected) < 60:
        print('ERR insufficient',code,len(collected))
        continue
    # collected currently has chunks with newest-first ordering per chunk; overall it's newest-first; reverse to chronological
    # but first we need to dedupe in case of overlap
    # build map by date keeping unique dates
    unique = {}
    for item in collected:
        d = item.get('stck_bsop_date')
        if d not in unique:
            unique[d]=item
    # sort by date ascending
    dates_sorted = sorted(unique.keys())
    data = [unique[d] for d in dates_sorted]
    closes = [float(x['stck_clpr']) for x in data]
    highs = [float(x['stck_hgpr']) for x in data]
    lows = [float(x['stck_lwpr']) for x in data]
    vols = [int(x['acml_vol']) for x in data]
    dates = [x['stck_bsop_date'] for x in data]
    n = len(closes)
    # compute SMA20 and RSI14
    def sma(arr,idx,period):
        if idx+1 < period: return None
        return sum(arr[idx+1-period:idx+1])/period
    def rsi_series(prices,period=14):
        deltas = [prices[i]-prices[i-1] for i in range(1,len(prices))]
        gains=[max(d,0) for d in deltas]
        losses=[max(-d,0) for d in deltas]
        avg_gain=sum(gains[:period])/period
        avg_loss=sum(losses[:period])/period
        rs_series=[None]*(period)
        for i in range(period,len(deltas)):
            avg_gain=(avg_gain*(period-1)+gains[i])/period
            avg_loss=(avg_loss*(period-1)+losses[i])/period
            if avg_loss==0:
                rs_series.append(100.0)
            else:
                rs=(avg_gain/avg_loss)
                rs_series.append(100 - (100/(1+rs)))
        return [None]+rs_series  # align length with prices (approx)
    rsi_vals = rsi_series(closes,14)
    # simulate
    cash = initial_cap
    position = 0.0
    entry_price = None
    trades = []
    peak_equity = initial_cap
    equity_curve = []
    for i in range(n):
        price = closes[i]
        sma20 = sma(closes,i,20)
        rsi = rsi_vals[i] if i < len(rsi_vals) else None
        # skip until indicators available
        if sma20 is None or rsi is None:
            equity = cash + position*price
            equity_curve.append(equity)
            peak_equity = max(peak_equity,equity)
            continue
        # buy signal: price crosses above sma20 (today> sma20 and yesterday <= sma20) and rsi>=40
        prev_price = closes[i-1]
        prev_sma20 = sma(closes,i-1,20)
        buy=False
        if prev_sma20 is not None:
            if prev_price <= prev_sma20 and price > sma20 and rsi>=40 and position==0:
                buy=True
        if buy:
            # buy max shares with cash
            qty = math.floor((cash/(price*(1+slippage_pct+fee_pct)))/1)  # unit 1 share
            if qty>0:
                trade_cost = qty*price*(1+slippage_pct+fee_pct)
                cash -= trade_cost
                position += qty
                entry_price = price
                trades.append({'side':'BUY','price':price,'qty':qty,'date':dates[i]})
        # sell: price crosses below sma20 or rsi>=70
        sell=False
        if position>0:
            if price < sma20 or rsi>=70:
                sell=True
        if sell and position>0:
            qty = position
            proceeds = qty*price*(1 - slippage_pct - fee_pct)
            cash += proceeds
            pnl = (price - entry_price)*qty - (entry_price*qty*(slippage_pct+fee_pct)) - (price*qty*(slippage_pct+fee_pct))
            trades.append({'side':'SELL','price':price,'qty':qty,'date':dates[i],'pnl':pnl})
            position = 0
            entry_price = None
        equity = cash + position*price
        equity_curve.append(equity)
        peak_equity = max(peak_equity,equity)
    # close remaining position at last price
    if position>0:
        price=closes[-1]
        proceeds = position*price*(1 - slippage_pct - fee_pct)
        cash += proceeds
        pnl = (price - entry_price)*position - (entry_price*position*(slippage_pct+fee_pct)) - (price*position*(slippage_pct+fee_pct))
        trades.append({'side':'SELL','price':price,'qty':position,'date':dates[-1],'pnl':pnl})
        position=0
    final_equity = cash
    total_return_pct = (final_equity - initial_cap)/initial_cap*100
    realized_pnl = final_equity - initial_cap
    wins = [t for t in trades if t.get('side')=='SELL' and t.get('pnl',0)>0]
    sell_trades = [t for t in trades if t.get('side')=='SELL']
    win_rate = (len(wins)/len(sell_trades))*100 if sell_trades else 0
    # MDD
    peak = -1e18
    mdd = 0
    for e in equity_curve:
        if e>peak:
            peak=e
        dd = (peak - e)/peak*100 if peak>0 else 0
        if dd>mdd: mdd=dd
    results[code] = {
        'name':name,
        'total_return_pct':round(total_return_pct,2),
        'realized_pnl':round(realized_pnl,2),
        'win_rate_pct':round(win_rate,2),
        'mdd_pct':round(mdd,2),
        'trades':len(trades)
    }
    time.sleep(1.5)

print(json.dumps(results,ensure_ascii=False,indent=2))
