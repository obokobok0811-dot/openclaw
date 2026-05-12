#!/usr/bin/env python3
import os
from pathlib import Path
import requests

# load .env.kis
env_path = Path(__file__).parent / '.env.kis'
if not env_path.exists():
    raise SystemExit('Missing .env.kis')
with open(env_path) as f:
    for line in f:
        if '=' in line:
            k,v = line.strip().split('=',1)
            os.environ[k]=v.strip('"')

APP_KEY = os.getenv('KIS_APP_KEY')
APP_SECRET = os.getenv('KIS_APP_SECRET')
CANO = os.getenv('KIS_ACCOUNT')
if not (APP_KEY and APP_SECRET and CANO):
    raise SystemExit('KIS_APP_KEY/KIS_APP_SECRET/KIS_ACCOUNT must be set')

TOKEN_URL = 'https://openapivts.koreainvestment.com:29443/oauth2/token'
payload = {'grant_type':'client_credentials','appkey':APP_KEY,'appsecret':APP_SECRET}
resp = requests.post(TOKEN_URL, data=payload, timeout=10)
resp.raise_for_status()
token = resp.json().get('access_token')
if not token:
    print('NO_TOKEN', resp.text)
    raise SystemExit(1)

# Force headers using exact env values and token
headers = {
    'appkey': APP_KEY,
    'appsecret': APP_SECRET,
    'Authorization': 'Bearer ' + token,
    'Content-Type': 'application/json; charset=utf-8'
}

ORDER_URL = 'https://openapivts.koreainvestment.com:29443/uapi/domestic-stock/v1/trading/order-cash'
# Build minimal JSON payload with numeric fields as strings per spec
payload = {
    'CANO': CANO,
    'ACNT_PRDT_CD': '01',
    'PDNO': '028260',
    'ORD_DVSN': '01',
    'ORD_QTY': '1',
    'ORD_UNPR': '0',
    'BUY_SELL': '1'
}
# Required headers for mock trading
headers['tr_id'] = 'VTTC0802U'

# Domain check
if not ORDER_URL.startswith('https://openapivts.koreainvestment.com:29443'):
    raise SystemExit('ORDER_URL domain mismatch')

r = requests.post(ORDER_URL, json=payload, headers=headers, timeout=10)
print('STATUS', r.status_code)
# Print response headers (non-sensitive) and body
resp_headers = dict(r.headers)
# remove potentially sensitive headers
for h in ['Set-Cookie','Authorization','authorization','appkey','appsecret']:
    resp_headers.pop(h, None)
print('RESP_HEADERS', resp_headers)
try:
    print(r.json())
except Exception:
    print(r.text)
