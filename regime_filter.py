#!/usr/bin/env python3
import os, time, requests, json
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

# fetch 1 year daily index chart for KOSPI (code 0001) using index-chart endpoint per spec
params = {
    'REDACTED':'J',
    'FID_INPUT_ISCD':'005930',
    'FID_INPUT_DATE_1':'20250509',
    'FID_INPUT_DATE_2':'20260509',
    'FID_PERIOD_DIV_CODE':'D',
    'FID_ORG_ADJ_PRC':'0'
}
url = base + '/uapi/domestic-stock/v1/quotations/REDACTED'
headers = {**headers_base, 'tr_id':'FHKST03010100'}

r = requests.get(url, params=params, headers=headers, timeout=30)
if r.status_code!=200:
    raise SystemExit(f'API_ERR {r.status_code} {r.text[:200]}')

j = r.json()
# find list in known keys
arr = None
for k in ['output2','output1','output','outputData']:
    v = j.get(k)
    if isinstance(v, list):
        arr = v
        break
if arr is None:
    for v in j.values():
        if isinstance(v, list):
            arr=v
            break
if not arr:
    raise SystemExit('No data in response')
# extract OHLC by date, response likely newest-first
closes = []
highs = []
lows = []
dates = []
for item in arr:
    if isinstance(item, dict):
        d = item.get('stck_bsop_date') or item.get('date')
        c = item.get('stck_clpr') or item.get('stck_prpr') or item.get('close')
        h = item.get('stck_hgpr') or item.get('stck_mxpr') or item.get('high')
        l = item.get('stck_lwpr') or item.get('stck_llam') or item.get('low')
        if d and c is not None:
            try:
                closes.append(float(c))
                highs.append(float(h) if h is not None else float(c))
                lows.append(float(l) if l is not None else float(c))
                dates.append(d)
            except:
                continue
# chronological ascending
closes = list(reversed(closes))
highs = list(reversed(highs))
lows = list(reversed(lows))
dates = list(reversed(dates))
if len(closes) < 60:
    raise SystemExit('Insufficient index data')
# current index = last element
current = closes[-1]
# SMA60 = mean of last 60 closes
sma60 = sum(closes[-60:])/60.0
regime = 'BULL' if current > sma60 else 'BEAR'
# save to state
state_dir = Path(__file__).parent / 'state'
state_dir.mkdir(exist_ok=True)
state_file = state_dir / 'market_regime.json'
with open(state_file,'w') as f:
    json.dump({'market_regime':regime,'current':current,'sma60':sma60,'date':dates[-1]},f)
# persist raw fetched series for ATR calculation by router
series_file = state_dir / '005930_series.json'
try:
    with open(series_file,'w') as sf:
        json.dump({'dates':dates,'closes':closes,'highs':highs,'lows':lows}, sf)
except Exception:
    pass

# persist raw fetched rows to CSV (append) for durability
try:
    from data_io import append_price_csv
    rows = []
    for d,c in zip(dates,closes):
        rows.append({'date':d,'close':c})
    append_price_csv('005930', rows)
except Exception:
    pass

print(regime)
