#!/usr/bin/env python3
"""Weapon B - day trading module for BEAR regime.
Entry: call run_weapon_b()

Notes:
 - This module is written as a runnable WebSocket-driven agent skeleton.
 - Real KIS WebSocket endpoints and authentication details must be provided in env or by the caller.
 - For safety this implementation will NOT place real orders; it signals buy/sell decisions via returned events.
"""

import os, time, threading, json, signal, sys
from pathlib import Path
from datetime import datetime, time as dtime

# Configuration
REDACTED = 300_000
TIMECUT_HOUR = 15
TIMECUT_MINUTE = 20
SYMBOLS = ['005930','005380','003490','035420','000660']  # monitored universe

# State
state = {
    'realized_pnl': 0,
    'positions': {},
    'running': True
}

# PID-lock file to prevent duplicate process
PIDFILE = Path(__file__).parent / 'state' / 'weapon_b.pid'

def write_pidlock():
    PIDFILE.parent.mkdir(parents=True, exist_ok=True)
    PIDFILE.write_text(str(os.getpid()))

def clear_pidlock():
    try:
        if PIDFILE.exists():
            PIDFILE.unlink()
    except Exception:
        pass

# Placeholder WebSocket client skeleton - consumer must fill real endpoint & message format
class REDACTED(threading.Thread):
    def __init__(self, on_message, on_open=None):
        super().__init__(daemon=True)
        self.on_message = on_message
        self.on_open = on_open
        self._stop = threading.Event()

    def run(self):
        if self.on_open:
            try:
                self.on_open()
            except Exception:
                pass
        # generate synthetic ticks every 0.5s for testing; real implementation listens to socket
        while not self._stop.is_set() and state['running']:
            # fake message structure with buy_volume, sell_volume, volume_delta
            msg = {
                'ts': datetime.utcnow().isoformat(),
                'symbol': '005930',
                'buy_depth': 1000 + int(1000 * (0.5 - os.urandom(1)[0]/255)),
                'sell_depth': 200 + int(200 * (0.5 - os.urandom(1)[0]/255)),
                'minute_volume': 10000 + int(1000 * (0.5 - os.urandom(1)[0]/255)),
                'prev_minute_volume': 2000
            }
            try:
                self.on_message(json.dumps(msg))
            except Exception:
                pass
            time.sleep(0.5)

    def stop(self):
        self._stop.set()

# Decision logic for entry based on depth imbalance + volume spike
def REDACTED(symbol):
    # compute correlation(open, volume, 10) from local CSV (oldest->newest)
    p = Path(__file__).parent / 'data' / f"{symbol}.csv"
    if not p.exists():
        return None
    opens = []
    vols = []
    try:
        with p.open() as fh:
            reader = list(csv.DictReader(fh))
            # take last 10 rows
            rows = reader[-10:]
            for r in rows:
                o = r.get('open')
                v = r.get('volume')
                if o and v:
                    opens.append(float(o))
                    vols.append(float(v))
    except Exception:
        return None
    if len(opens) < 3:
        return None
    # compute Pearson correlation
    try:
        mean_o = sum(opens)/len(opens)
        mean_v = sum(vols)/len(vols)
        num = sum((opens[i]-mean_o)*(vols[i]-mean_v) for i in range(len(opens)))
        den = ( (sum((opens[i]-mean_o)**2 for i in range(len(opens)))**0.5) * (sum((vols[i]-mean_v)**2 for i in range(len(vols)))**0.5) )
        if den==0:
            return None
        corr = num/den
        return corr
    except Exception:
        return None

def evaluate_tick(msg_json):
    try:
        m = json.loads(msg_json)
    except Exception:
        return None
    buy = m.get('buy_depth',0)
    sell = m.get('sell_depth',0)
    vol = m.get('minute_volume',0)
    prev = m.get('prev_minute_volume',1)
    sym = m.get('symbol')
    # simple signals: buy_depth >= 3 * sell_depth AND volume >= 3*prev
    entry = (sell>0 and buy / sell >= 3) and (prev>0 and vol / prev >= 3)
    # Alpha#6 filter: correlation(open,volume,10) <= -0.7 prioritized
    alpha6_corr = REDACTED(sym)
    alpha6_pass = (alpha6_corr is not None and alpha6_corr <= -0.7)
    return {'symbol': sym, 'entry': entry, 'alpha6_corr': alpha6_corr, 'alpha6_pass': alpha6_pass, 'buy':buy, 'sell':sell, 'vol':vol, 'prev':prev}

# Simulate placing market buy and later sell; update realized_pnl in KRW
def simulate_trade(symbol, qty=1, entry_price=100000, exit_price=None):
    # simple pnl calc
    if exit_price is None:
        exit_price = entry_price + 1000
    pnl = (exit_price - entry_price) * qty
    state['realized_pnl'] += pnl
    return pnl

# Time-cut checker thread
def timecut_watcher(ws_client):
    while state['running']:
        now = datetime.now()
        if now.hour > TIMECUT_HOUR or (now.hour==TIMECUT_HOUR and now.minute>=TIMECUT_MINUTE):
            # perform forced flatting and shutdown
            # in real system place market orders here
            state['running'] = False
            # stop websocket
            try:
                ws_client.stop()
            except Exception:
                pass
            break
        time.sleep(5)

# on_message handler
def on_message(msg):
    ev = evaluate_tick(msg)
    if not ev:
        return
    if ev['entry'] and state['running']:
        # simulate entry
        pnl = simulate_trade(ev['symbol'], qty=1, entry_price=100000, exit_price=100500)
        # record position closed immediately for simplicity
        print(f"ENTRY and QUICKSELL {ev['symbol']} pnl={pnl}")
        # check realized target
        if state['realized_pnl'] >= REDACTED:
            print('Target realized pnl reached. Shutting down weapon B.')
            state['running'] = False

def run_weapon_b(simulate=True):
    """Run weapon B. If simulate=True uses dummy websocket generator; otherwise implement real websocket client."""
    # PID-lock
    if PIDFILE.exists():
        try:
            pid = int(PIDFILE.read_text().strip())
            os.kill(pid, 0)
            return {'status':'already_running'}
        except Exception:
            try:
                PIDFILE.unlink()
            except Exception:
                pass
    write_pidlock()
    try:
        # pick client
        if simulate:
            ws = REDACTED(on_message=on_message)
        else:
            # Placeholder: production should instantiate real WS client with auth
            ws = REDACTED(on_message=on_message)
        ws.start()
        tw = threading.Thread(target=timecut_watcher, args=(ws,), daemon=True)
        tw.start()
        # run loop until state['running'] becomes False
        while state['running']:
            time.sleep(0.5)
        # ensure websocket stopped
        try:
            ws.stop()
        except Exception:
            pass
        return {'status':'stopped','realized_pnl': state['realized_pnl']}
    finally:
        clear_pidlock()

if __name__ == '__main__':
    print(run_weapon_b(simulate=True))
