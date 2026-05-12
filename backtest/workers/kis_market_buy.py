"""
kis_market_buy.py — safe DRY_RUN-only stub for recovery
This file is a safety-preserving version: DRY_RUN always True, no network calls.
"""
import time, json

DRY_RUN = True
ORDERS = [
    {"ticker":"009150","qty":2},
    {"ticker":"307950","qty":3},
    {"ticker":"120110","qty":21},
    {"ticker":"375500","qty":20},
    {"ticker":"298020","qty":4},
]
LOG = '/Users/andy/.openclaw/workspace/backtest/workers/kis_market_buy.log'

def write_log(line):
    ts = time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime())
    s = f"{ts} {line}"
    try:
        with open(LOG,'a') as f:
            f.write(s+"\n")
    except Exception:
        pass
    print(s)

def main():
    write_log('SAFEMODE: kis_market_buy.py starting with DRY_RUN=True (no network calls)')
    results = {}
    for o in ORDERS:
        sim = {"status":"simulated","http_status":200,"response":{"rt_cd":"0","result":{"ORDERNO":f"SAFE-{int(time.time())}-{o['ticker']}"}}}
        write_log(f"SIM ORDER {o['ticker']}: {json.dumps(sim, ensure_ascii=False)}")
        results[o['ticker']] = sim
    write_log('SAFEMODE batch finished')
    write_log(json.dumps(results, ensure_ascii=False))

if __name__=='__main__':
    main()
