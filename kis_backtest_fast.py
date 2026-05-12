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

# date range per instruction
date_from='20250508'
date_to='20260508'

for code,name in symbols:
    time.sleep(1.5)
    params = {
        'REDACTED':'J',
        'FID_INPUT_ISCD':code,
        'FID_INPUT_DATE_1':date_from,
        'FID_INPUT_DATE_2':date_to,
        'FID_PERIOD_DIV_CODE':'D',
        'FID_ORG_ADJ_PRC':'0'
    }
    headers = {**headers_base, 'tr_id':'FHKST03010100'}
    url = base + '/uapi/domestic-stock/v1/quotations/REDACTED'
    r = requests.get(url, params=params, headers=headers, timeout=30)
    if r.status_code!=200:
        print('ERR',code,r.status_code,r.text[:200])
        continue
    j = r.json()
    # prefer list-valued outputs in known keys
    arr = None
    for k in ['output2','output1','output','outputData']:
        v = j.get(k)
        if isinstance(v, list):
            arr = v
            break
    if arr is None:
        # fallback: find any list in json values
        for v in j.values():
            if isinstance(v, list):
                arr = v
                break
    # if still None, maybe fields are nested inside a dict; try output2->somekey
    if arr is None:
        for k in ['output2','output1','output','outputData']:
            v = j.get(k)
            if isinstance(v, dict):
                for vv in v.values():
                    if isinstance(vv, list):
                        arr = vv
                        break
                if arr is not None:
                    break
    # sometimes API returns a JSON-encoded string inside the field
    if isinstance(arr, str):
        try:
            import json as _json
            arr_parsed = _json.loads(arr)
            if isinstance(arr_parsed, list):
                arr = arr_parsed
        except Exception:
            pass
    if not arr:
        print('ERR no data',code,j)
        continue
    # assume arr is chronological or latest-first; detect by dates
    # extract date and close
    data_map = {}
    for item in arr:
        if isinstance(item, str):
            try:
                import json as _json
                item = _json.loads(item)
            except Exception:
                continue
        if not isinstance(item, dict):
            continue
        d = item.get('stck_bsop_date') or item.get('date') or item.get('base_date')
        close = item.get('stck_clpr') or item.get('stck_prpr') or item.get('close')
        high = item.get('stck_hgpr') or item.get('high')
        low = item.get('stck_lwpr') or item.get('low')
        vol = item.get('acml_vol') or item.get('acml_trvla') or item.get('vol')
        if d and close is not None:
            try:
                data_map[d]= {'date':d,'close':float(close),'high':float(high) if high else None,'low':float(low) if low else None,'vol':int(vol) if vol else None}
            except Exception:
                continue
    dates_sorted = sorted(data_map.keys())
    data = [data_map[d] for d in dates_sorted]
    if len(data) < 60:
        print('ERR insufficient',code,len(data))
        continue
    closes = [x['close'] for x in data]
    dates = [x['date'] for x in data]
    n = len(closes)
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
        return [None]+rs_series
    rsi_vals = rsi_series(closes,14)
    cash = initial_cap
    position = 0.0
    entry_price = None
    trades = []
    equity_curve = []
    for i in range(n):
        price = closes[i]
        sma20 = sma(closes,i,20)
        rsi = rsi_vals[i] if i < len(rsi_vals) else None
        if sma20 is None or rsi is None:
            equity = cash + position*price
            equity_curve.append(equity)
            continue
        # relaxed buy: price below SMA20 and RSI <=40 (less strict)
        buy=False
        if sma20 is not None and rsi is not None and position==0:
            if price < sma20 and rsi <= 40:
                buy=True
        if buy:
            qty = math.floor((cash/(price*(1+slippage_pct+fee_pct)))/1)
            if qty>0:
                trade_cost = qty*price*(1+slippage_pct+fee_pct)
                cash -= trade_cost
                position += qty
                entry_price = price
                trades.append({'side':'BUY','price':price,'qty':qty,'date':dates[i]})
        # new sell: price touches/reaches SMA20 (price >= sma20) or RSI >= 60
        sell=False
        if position>0 and sma20 is not None and rsi is not None:
            if price >= sma20 or rsi >= 60:
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
