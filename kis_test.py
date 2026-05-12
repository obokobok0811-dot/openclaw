#!/usr/bin/env python3
import os
import requests
from pathlib import Path

# Load .env.kis
env_path = Path(__file__).parent / '.env.kis'
if not env_path.exists():
    raise SystemExit(f"Missing {env_path}; create it with KIS_APP_KEY, KIS_APP_SECRET, KIS_ACCOUNT")
with open(env_path) as f:
    for line in f:
        if '=' in line:
            k,v = line.strip().split('=',1)
            os.environ[k]=v.strip('"')

APP_KEY = os.getenv('KIS_APP_KEY')
APP_SECRET = os.getenv('KIS_APP_SECRET')
if not APP_KEY or not APP_SECRET:
    raise SystemExit('KIS_APP_KEY and KIS_APP_SECRET must be set in .env.kis')

# KIS token endpoint (mocking path used by Korean Investment API)
TOKEN_URL = 'https://openapivts.koreainvestment.com:29443/oauth2/token'  # token endpoint

payload = {
    'grant_type': 'client_credentials',
    'appkey': APP_KEY,
    'appsecret': APP_SECRET
}

try:
    resp = requests.post(TOKEN_URL, data=payload, timeout=10, verify=True)
    resp.raise_for_status()
    print('ACCESS_TOKEN_OK')
    print(resp.json())
except Exception as e:
    print('ACCESS_TOKEN_FAIL')
    print(str(e))
