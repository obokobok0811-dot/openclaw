#!/usr/bin/env python3
import websocket, json, time, threading
from datetime import datetime, timezone, timedelta
import ssl

# Force a reusable KST timezone object for all timestamps
KST = timezone(timedelta(hours=9))
LOG = '/Users/andy/.openclaw/workspace/monitor_alerts.log'
MARKETS = ["KRW-ETH","KRW-ARB","KRW-OP","KRW-SHIB","KRW-PENGU"]
URL = 'wss://api.upbit.com/websocket/v1'

def log(msg):
    # Use the global KST timezone object
    ts = datetime.now(KST).isoformat(sep=' ')
    with open(LOG, 'a') as f:
        f.write(f"{ts} {msg}\n")


def on_message(ws, message):
    try:
        data = json.loads(message)
    except Exception:
        return
    # Upbit websocket may send arrays
    if isinstance(data, list):
        for entry in data:
            if entry.get('type') == 'ticker' or entry.get('code'):
                market = entry.get('code') or entry.get('market')
                price = entry.get('trade_price') or entry.get('tp') or entry.get('tradePrice')
                log(f"REDACTED {market} {price}")
                # After first receipt, keep logging ticks
                break
    else:
        market = data.get('code') or data.get('market')
        price = data.get('trade_price') or data.get('tp')
        log(f"TICK {market} {price}")


def on_open(ws):
    log('CONNECTED')
    # subscribe
    req = [{"ticket":"connect"}]
    for m in MARKETS:
        req.append({"type":"ticker","codes":[m]})
    ws.send(json.dumps(req))


def on_error(ws, err):
    log(f"ERROR {err}")


def on_close(ws, code, reason):
    log(f"CLOSED {code} {reason}")


def run():
    websocket.enableTrace(False)
    ws = websocket.WebSocketApp(URL,
                                on_open=on_open,
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close)
    ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})

if __name__ == '__main__':
    log('SCRIPT_STARTED')
    run()
