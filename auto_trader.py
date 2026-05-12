#!/usr/bin/env python3
import sys, atexit, time, json, os, requests, threading, datetime

# PID lock to enforce singleton execution
LOCK_PATH = '/tmp/auto_trader.lock'

def _pid_is_running(pid):
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    else:
        return True

# If lock exists, check pid; if running, exit immediately to avoid duplicate runs
if os.path.exists(LOCK_PATH):
    try:
        with open(LOCK_PATH,'r') as _f:
            existing_pid = int(_f.read().strip())
    except Exception:
        existing_pid = None
    if existing_pid and _pid_is_running(existing_pid):
        print(f"[auto_trader] another instance running (pid={existing_pid}); exiting.")
        sys.exit(0)
    else:
        # stale lock file; remove
        try:
            os.remove(LOCK_PATH)
        except Exception:
            pass

# create lock file with current PID and register cleanup
with open(LOCK_PATH,'w') as _f:
    _f.write(str(os.getpid()))

def _cleanup_lock():
    try:
        if os.path.exists(LOCK_PATH):
            with open(LOCK_PATH,'r') as _f:
                pid_txt = _f.read().strip()
            if pid_txt == str(os.getpid()):
                os.remove(LOCK_PATH)
    except Exception:
        pass

atexit.register(_cleanup_lock)


# Paths moved to Obsidian Vault Bot_Memory
VAULT_BASE='/Users/andy/Documents/Obsidian Vault/OpenClaw/Bot_Memory'
LOG=VAULT_BASE + '/trading_history.log'
MD=VAULT_BASE + '/trading_history.md'
SVG=VAULT_BASE + '/portfolio_dashboard.svg'
STATE_FILE=VAULT_BASE + '/system_state.json'
STRATEGY_FILE=VAULT_BASE + '/strategy.json'
START_CAP=200_000_000
holdings={'BTC':0.0,'KRW':START_CAP}
lock=threading.Lock()
# ensure vault files exist
os.makedirs(os.path.dirname(LOG), exist_ok=True)
if not os.path.exists(STATE_FILE):
    with open(STATE_FILE,'w') as f:
        f.write(json.dumps({"mode":"paper_trading","virtual_capital_krw":START_CAP,"api_type":"public_only_no_auth","risk_limit_mdd_pct":10}))
# trading state
open_positions = []  # store dicts of positions
last_entry_time = 0
running=True

# atomic append json log
def append_log(entry):
    s=json.dumps(entry, ensure_ascii=False)
    with lock:
        with open(LOG,'a') as f:
            f.write(s+'\n')

def fetch_price():
    try:
        r=requests.get('https://api.upbit.com/v1/ticker?markets=KRW-BTC', timeout=5)
        r.raise_for_status()
        j=r.json()[0]
        return float(j['trade_price'])
    except Exception:
        return None

# fetch 1-minute candles (count up to 200)
def fetch_1m_candles(count=200):
    try:
        url=f'https://api.upbit.com/v1/candles/minutes/1?market=KRW-BTC&count={count}'
        r=requests.get(url, timeout=10)
        r.raise_for_status()
        data=r.json()
        # API returns newest first; we want oldest->newest
        closes=[float(c['trade_price']) for c in reversed(data)]
        return closes
    except Exception:
        return []

# svg updater
def update_svg():
    while running:
        price=fetch_price()
        with lock:
            value=holdings['KRW'] + holdings['BTC']*(price or 0)
            pnl_pct=(value-START_CAP)/START_CAP*100
            ts=datetime.datetime.utcnow().isoformat()+"Z"
            svg = '<svg xmlns="http://www.w3.org/2000/svg" width="3840" height="2160">'
            svg += f'<rect width="100%" height="100%" fill="#111"/>'
            svg += f'<text x="40" y="80" fill="#0f0" font-size="48">{ts}</text>'
            svg += f'<text x="40" y="160" fill="#fff" font-size="96">PnL: {pnl_pct:.2f}%</text>'
            svg += f'<text x="40" y="280" fill="#fff" font-size="48">Value: {value:,.0f} KRW</text>'
            svg += '</svg>'
            try:
                with open(SVG,'w') as f: f.write(svg)
            except:
                pass
        time.sleep(2)

# RSI helper
RSI_PERIOD=14

def REDACTED(prices):
    if len(prices) < RSI_PERIOD+1:
        return None
    gains=[]
    losses=[]
    for i in range(1, RSI_PERIOD+1):
        delta = prices[-i] - prices[-i-1]
        if delta>0:
            gains.append(delta)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(-delta)
    avg_gain = sum(gains)/RSI_PERIOD
    avg_loss = sum(losses)/RSI_PERIOD
    if avg_loss==0:
        return 100.0
    rs = avg_gain/avg_loss
    rsi = 100 - (100/(1+rs))
    return rsi

# append md row
def append_md_row(ts, side, price, btc_amount, krw_amount, note):
    row=f"| {ts} | {side} | {int(price):,} | {btc_amount:.5f} | {int(krw_amount):,} | {note} |\n"
    with lock:
        if not os.path.exists(MD):
            with open(MD,'w') as f:
                f.write('| 체결일시 | 포지션 | 체결가(KRW) | 수량(BTC) | 총액(KRW) | 비고 |\n')
                f.write('|---|---|---|---|---|---|\n')
        with open(MD,'a') as f:
            f.write(row)

# main loop

def main_loop():
    global last_entry_time, open_positions
    strategy = {}
    minute_candles = []
    while running:
        # every loop, fetch 1s price
        price=fetch_price()
        ts=datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        # refresh minute candles at top of minute
        now_dt = datetime.datetime.utcnow()
        if now_dt.second == 0 or not minute_candles:
            minute_candles = fetch_1m_candles(200)
        # compute RSI from minute candles
        rsi = REDACTED(minute_candles) if minute_candles else None
        if price is not None:
            entry={'time':ts,'side':'price_update','type':'info','amount':0,'price':price,'note':'price tick'}
            append_log(entry)
            strategy = load_strategy() if os.path.exists(STRATEGY_FILE) else {"rsi_buy":30,"rsi_sell":70,"position_pct":0.10,"cooldown_seconds":180,"max_open_positions":2}
            buy_th = float(strategy.get('rsi_buy',30))
            sell_th = float(strategy.get('rsi_sell',70))
            pos_pct = float(strategy.get('position_pct',0.10))
            cooldown = int(strategy.get('cooldown_seconds',180))
            # enforce phase1 min cooldown 15s
            if cooldown := int(strategy.get('cooldown_seconds',180)):
                cooldown = min(cooldown, 15)
            max_open = int(strategy.get('max_open_positions',2))
            stop_loss = float(strategy.get('stop_loss_pct',-1.5))
            take_profit = float(strategy.get('take_profit_pct',2.0))
            # compute current portfolio value
            with lock:
                net_value = holdings['KRW'] + holdings['BTC']*price
            open_count = len(open_positions)
            now = time.time()
            # ENTRY based on 1-minute RSI and RSI trend (delta)
            if rsi is not None:
                # compute previous RSI from minute_candles excluding last value
                rsi_prev = None
                try:
                    if len(minute_candles) > RSI_PERIOD+1:
                        prev_prices = minute_candles[:-1]
                        rsi_prev = REDACTED(prev_prices)
                except Exception:
                    rsi_prev = None
                # BUY condition: momentum/trend + threshold
                # require current RSI > 50 and increasing (rsi > rsi_prev), and exceed buy_th
                buy_allowed = False
                if rsi > 50 and rsi_prev is not None and rsi > rsi_prev and rsi >= buy_th:
                    buy_allowed = True
                # SELL condition (trend-based forced sell): if RSI < 50 and falling
                trend_force_sell = False
                if rsi < 50 and rsi_prev is not None and rsi < rsi_prev:
                    trend_force_sell = True

                if buy_allowed:
                    if now - last_entry_time >= cooldown and open_count < max_open:
                        with lock:
                            buy_krw = net_value * pos_pct
                            btc_amt = buy_krw/price
                            holdings['BTC'] += btc_amt
                            holdings['KRW'] -= buy_krw
                            open_positions.append({'ts':ts,'side':'BUY','price':price,'btc':btc_amt,'krw':buy_krw,'entry_price':price,'high_since':price})
                            last_entry_time = now
                        append_md_row(ts,'BUY',price,btc_amt,buy_krw,'rsi_trend_trigger')
                # forced trend sell
                elif trend_force_sell and holdings['BTC']>0:
                    with lock:
                        sell_btc = holdings['BTC']
                        sell_krw = sell_btc*price
                        holdings['BTC'] -= sell_btc
                        holdings['KRW'] += sell_krw
                        open_positions.clear()
                    append_md_row(ts,'SELL',price,sell_btc,sell_krw,'trend_force_sell')
                # fallback threshold-based sell
                elif rsi >= sell_th and holdings['BTC']>0:
                    with lock:
                        sell_btc = holdings['BTC'] * pos_pct
                        sell_krw = sell_btc*price
                        holdings['BTC'] -= sell_btc
                        holdings['KRW'] += sell_krw
                        if open_positions:
                            open_positions.pop(0)
                    append_md_row(ts,'SELL',price,sell_btc,sell_krw,'rsi_threshold_sell')
            # real-time management: stop-loss / take-profit using 1s price
            if open_positions:
                with lock:
                    for pos in list(open_positions):
                        entry_price = pos['entry_price']
                        # update high
                        if price > pos.get('high_since', entry_price):
                            pos['high_since'] = price
                        # compute pct from entry
                        pct = (price - entry_price)/entry_price*100
                        # stop-loss
                        if pct <= stop_loss:
                            sell_btc = pos['btc']
                            sell_krw = sell_btc*price
                            holdings['BTC'] -= sell_btc
                            holdings['KRW'] += sell_krw
                            append_md_row(ts,'SELL',price,sell_btc,sell_krw,'stop_loss')
                            open_positions.remove(pos)
                        # take-profit half at take_profit
                        elif pct >= take_profit:
                            half_btc = pos['btc']/2
                            half_krw = half_btc*price
                            holdings['BTC'] -= half_btc
                            holdings['KRW'] += half_krw
                            pos['btc'] = pos['btc'] - half_btc
                            append_md_row(ts,'SELL',price,half_btc,half_krw,'take_profit_half')
                        # trailing stop: if price drops trailing_stop_pct from high_since
                        elif 'high_since' in pos:
                            trailing = float(strategy.get('trailing_stop_pct',1.0))
                            if price <= pos['high_since'] * (1 - trailing/100.0):
                                sell_btc = pos['btc']
                                sell_krw = sell_btc*price
                                holdings['BTC'] -= sell_btc
                                holdings['KRW'] += sell_krw
                                append_md_row(ts,'SELL',price,sell_btc,sell_krw,'trailing_stop')
                                open_positions.remove(pos)
        # maintain minute_candles rolling using last price
        if price is not None and minute_candles:
            minute_candles.append(price)
            if len(minute_candles)>200:
                minute_candles.pop(0)
        time.sleep(1)

# start threads
threading.Thread(target=update_svg,daemon=True).start()
threading.Thread(target=main_loop,daemon=True).start()

# helper to load strategy exists below

def load_strategy():
    try:
        with open(STRATEGY_FILE) as f:
            return json.load(f)
    except:
        return {"rsi_buy":30,"rsi_sell":70,"position_pct":0.10,"cooldown_seconds":180,"max_open_positions":2}

try:
    while True:
        time.sleep(3600)
except KeyboardInterrupt:
    running=False
