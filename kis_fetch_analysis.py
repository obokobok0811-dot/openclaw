#!/usr/bin/env python3
import os
from pathlib import Path
import requests
import sys

# load .env.kis
env_path = Path(__file__).parent / '.env.kis'
if not env_path.exists():
    print('ERR Missing .env.kis')
    sys.exit(1)
with open(env_path) as f:
    for line in f:
        if '=' in line:
            k,v = line.strip().split('=',1)
            os.environ[k]=v.strip('"')

APP_KEY = os.getenv('KIS_APP_KEY')
APP_SECRET = os.getenv('KIS_APP_SECRET')
CANO = os.getenv('KIS_ACCOUNT')
if not (APP_KEY and APP_SECRET):
    print('ERR missing keys')
    sys.exit(1)

# get token
TOKEN_URL = 'https://openapivts.koreainvestment.com:29443/oauth2/token'
payload = {'grant_type':'client_credentials','appkey':APP_KEY,'appsecret':APP_SECRET}
resp = requests.post(TOKEN_URL, data=payload, timeout=10)
resp.raise_for_status()
token = resp.json().get('access_token')
if not token:
    print('ERR no token')
    sys.exit(1)

headers = {
    'appkey': APP_KEY,
    'appsecret': APP_SECRET,
    'Authorization': 'Bearer ' + token,
    'Content-Type': 'application/json; charset=utf-8'
}
base='https://openapivts.koreainvestment.com:29443'

import time

# helper: GET with retry on rate-limit (EGW00201) or 500 that contains that code
def get_with_retry(url, params, headers, tr_id, max_attempts=3):
    headers = headers.copy()
    headers['tr_id'] = tr_id
    attempt = 0
    while attempt < max_attempts:
        attempt += 1
        r = requests.get(url, params=params, headers=headers, timeout=10)
        if r.status_code == 200:
            return r.json()
        # try to parse body for error code
        try:
            j = r.json()
            rt = j.get('msg_cd') or j.get('rt_cd') or ''
            msg = j.get('msg1') or ''
        except Exception:
            rt = ''
            msg = r.text
        if 'EGW00201' in rt or '초당 거래건수를 초과' in msg:
            if attempt < max_attempts:
                time.sleep(3)
                continue
            else:
                raise SystemExit(f'RATE_LIMIT {r.status_code} {msg}')
        else:
            # other error
            raise SystemExit(f'ERR {r.status_code} {msg}')
    raise SystemExit('UNRECOVERABLE')

# 1) current price - GET with query params
price_url = base + '/uapi/domestic-stock/v1/quotations/inquire-price'
params_price = {
    'REDACTED': 'J',
    'FID_INPUT_ISCD': '005380'
}
headers['tr_id']='FHKST01010100'
price_json = get_with_retry(price_url, params_price, headers, 'FHKST01010100')

# mandatory 1 second sleep between calls
time.sleep(1)

# 2) daily candles - GET with query params
daily_url = base + '/uapi/domestic-stock/v1/quotations/inquire-daily-price'
params_daily = {
    'REDACTED': 'J',
    'FID_INPUT_ISCD': '005380',
    'FID_PERIOD_DIV_CODE': 'D',
    'FID_ORG_ADJ_PRC': '0',
    'FID_INPUT_HOUR': '100'
}
headers['tr_id']='FHKST01010400'
# wait 60s to avoid throttling per user instruction
time.sleep(60)
daily_json = get_with_retry(daily_url, params_daily, headers, 'FHKST01010400')

# Extract arrays: assuming response format contains output2 or output array; try common keys
# Inspect structures
# For safety, print debug if unexpected

# Helpers
def get_list_from_resp(j):
    # try common keys
    for key in ['output','output2','output1','stck_prpr','output1']: 
        if key in j:
            return j[key]
    # sometimes nested
    for v in j.values():
        if isinstance(v, list):
            return v
    return None

price_list = get_list_from_resp(price_json) or [price_json]
daily_list = get_list_from_resp(daily_json)
if not daily_list:
    print('ERR no daily data', daily_json)
    sys.exit(1)

# Build close, high, low, volume arrays (most recent first?) KIS may return most recent first
closes=[]
highs=[]
lows=[]
vols=[]
dates=[]
for item in daily_list[:100]:
    # common keys
    close = item.get('stck_clpr') or item.get('stck_prpr') or item.get('close') or item.get('prdy_vrss_close')
    high = item.get('stck_hgpr') or item.get('high')
    low = item.get('stck_lwpr') or item.get('low')
    vol = item.get('acml_vol') or item.get('acml_trvla') or item.get('vol') or item.get('acc_trdvol')
    date = item.get('stck_bsop_date') or item.get('date')
    try:
        closes.append(float(close))
    except:
        closes.append(None)
    try:
        highs.append(float(high))
    except:
        highs.append(None)
    try:
        lows.append(float(low))
    except:
        lows.append(None)
    try:
        vols.append(float(vol))
    except:
        vols.append(None)
    dates.append(date)

# Remove entries with None closes
data = [(d,c,h,l,v) for d,c,h,l,v in zip(dates,closes,highs,lows,vols) if c is not None]
if len(data)<60:
    print('ERR insufficient data', len(data))
    sys.exit(1)

# Compute volume change using API ordering: daily_list[0]=latest, [1]=previous
vol_change = None
try:
    api_latest = float(daily_list[0].get('acml_vol') or daily_list[0].get('acml_trvla') or daily_list[0].get('vol'))
    api_prev = float(daily_list[1].get('acml_vol') or daily_list[1].get('acml_trvla') or daily_list[1].get('vol'))
    if api_prev>0:
        vol_change = (api_latest - api_prev)/api_prev*100
except Exception:
    vol_change = None

# data is in response order; assume most recent first; reverse to chronological for SMA/RSI
data = list(reversed(data))
dates, closes, highs, lows, vols = zip(*data)

import math
# Simple moving average
def sma(arr, n):
    return sum(arr[-n:])/n

sma5 = sma(closes,5)
sma20 = sma(closes,20)
sma60 = sma(closes,60)

# RSI(14)
def rsi(prices, period=14):
    deltas = [prices[i]-prices[i-1] for i in range(1,len(prices))]
    gains = [d if d>0 else 0 for d in deltas]
    losses = [-d if d<0 else 0 for d in deltas]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(deltas)):
        g = gains[i]
        l = losses[i]
        avg_gain = (avg_gain*(period-1)+g)/period
        avg_loss = (avg_loss*(period-1)+l)/period
    if avg_loss==0:
        return 100.0
    rs = avg_gain/avg_loss
    return 100 - (100/(1+rs))

rsi14 = rsi(list(closes),14)

# Volume change vs previous day
vol_change = None
if len(vols)>=2:
    vol_change = (vols[-1]-vols[-2])/vols[-2]*100 if vols[-2]>0 else None

# Determine order (정배열/역배열)
order_type = '정배열' if sma5>sma20 and sma20>sma60 else ('역배열' if sma5<sma20 and sma20<sma60 else '혼합')

# Output concise JSON
import json
out = {
    'symbol':'005380',
    'date': dates[-1],
    'close': closes[-1],
    'sma5': sma5,
    'sma20': sma20,
    'sma60': sma60,
    'order': order_type,
    'vol_change_pct': vol_change,
    'rsi14': rsi14
}
print(json.dumps(out))
