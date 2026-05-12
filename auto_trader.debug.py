#!/usr/bin/env python3
print('DEBUG_START',flush=True)
"""
auto_trader.py (Commander's Override Edition - LIVE)
Fully Autonomous Multi-Strike System: Supports Multi-Ticker, Safe Ledger Updates, Sell Logic,
with Pre/Post Logging, Transaction Rollback, and Webhook Alerts.
"""
import os
import json
import time
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from tools.ledger_utils import save_ledger, _make_trade_id

BASE = Path('/Users/andy/.openclaw/workspace')
LEDGER = BASE / 'REDACTED.json'
BACKUP_DIR = BASE

# load target tickers from config if present
try:
    with open(BASE / 'tools' / 'multi_ticker_config.json') as f:
        cfg = json.load(f)
        TARGET_TICKERS = cfg.get('TARGET_TICKERS', ['KRW-BTC','KRW-ETH'])
except Exception:
    TARGET_TICKERS = ['KRW-BTC', 'KRW-ETH', 'KRW-LINEA', 'KRW-TOKAMAK']

FEE_RATE = 0.0005
SLIPPAGE = 0.001
MIN_QTY = 1e-7
# Trading thresholds
REDACTED = float(os.environ.get('REDACTED', '0.24'))
# Candidate A defaults: TP 2%, SL -1%
SELL_TP = float(os.environ.get('SELL_TP', '0.02'))
SELL_SL = float(os.environ.get('SELL_SL', '-0.01'))
WEBHOOK_URL = os.environ.get('WEBHOOK_URL', '')
# External aggregator integration
REDACTED = os.environ.get('REDACTED','0') == '1'
AGG_PATH = BASE / 'sandbox_spio' / 'artifacts' / 'aggregator' / 'vote.json'
# Simulation toggle
SIMULATED = os.environ.get('SIMULATED','0') == '1'

# --- Core Helpers ---
def append_cron_log(msg):
    try:
        with open(BACKUP_DIR / 'cron_debug.log', 'a') as f:
            f.write(f"{datetime.now().isoformat()} - {msg}\n")
    except Exception:
        pass


def send_critical_alert(text):
    if not WEBHOOK_URL:
        return
    try:
        payload = {'timestamp': datetime.now().isoformat(), 'text': text}
        req = urllib.request.Request(WEBHOOK_URL, data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass


def load_ledger():
    if not LEDGER.exists():
        return {'trade_history': [], 'krw_balance': 198560000, 'positions': {}, 'meta': {}}
    try:
        return json.loads(LEDGER.read_text())
    except Exception:
        return {'trade_history': [], 'krw_balance': 198560000, 'positions': {}, 'meta': {}}


def get_live_upbit_data(market):
    url = f"https://api.upbit.com/v1/candles/minutes/1?market={market}&count=20"
    for _ in range(3):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=3) as response:
                data = json.loads(response.read().decode('utf-8'))
                prices = [candle['trade_price'] for candle in data]
                prices.reverse()

                gains = [prices[i] - prices[i-1] for i in range(1, len(prices)) if prices[i] - prices[i-1] > 0]
                losses = [abs(prices[i] - prices[i-1]) for i in range(1, len(prices)) if prices[i] - prices[i-1] < 0]
                avg_gain = sum(gains[-14:]) / 14 if len(gains) >= 14 else (sum(gains)/len(gains) if gains else 0)
                avg_loss = sum(losses[-14:]) / 14 if len(losses) >= 14 else (sum(losses)/len(losses) if losses else 0.0001)
                rs = avg_gain / avg_loss if avg_loss != 0 else 999
                rsi = 100 - (100 / (1 + rs))

                return {
                    'ticker': market,
                    'price': prices[-1],
                    'rsi': rsi,
                    'ema5': sum(prices[-5:]) / 5,
                    'ema20': sum(prices[-20:]) / 20 if len(prices) >= 20 else prices[-1],
                    'history_prices': prices
                }
        except Exception:
            time.sleep(1)
    return None


def compute_confidence(snapshot):
    if not snapshot:
        return 0.0
    price = snapshot['price']
    ema5, ema20, rsi = snapshot['ema5'], snapshot['ema20'], snapshot['rsi']

    rsi_score = max(0.0, min(1.0, abs(rsi - 50.0) / 50.0))
    momentum = (ema5 - ema20) / price if price > 0 else 0.0
    momentum_score = max(-1.0, min(1.0, momentum * 10.0))
    momentum_score = (momentum_score + 1.0) / 2.0

    conf = 0.5 * rsi_score + 0.5 * momentum_score
    return max(0.0, min(1.0, conf))

# --- Trade Execution & Accounting ---
def execute_trade(ticker, side, amount_krw, qty_coin, exec_price, ledger):
    global SIMULATED

    fee = amount_krw * FEE_RATE
    coin_sym = ticker.split('-')[1]

    # 0. State Backup for Rollback
    backup_krw = ledger.get('krw_balance', 0.0)
    backup_pos = ledger.get('positions', {}).get(coin_sym, 0.0)

    # 1. Detailed Logging: Pre-Trade
    append_cron_log(f"[PRE-TRADE] {side} {ticker} | KRW: {backup_krw:,.0f} | {coin_sym}: {backup_pos:.6f}")

    # 2. Update memory balances safely
    # timestamp for trade record
    timestamp = datetime.now().isoformat()

    if side == 'BUY':
        ledger['krw_balance'] -= (amount_krw + fee)
        ledger['positions'][coin_sym] = backup_pos + qty_coin
    elif side == 'SELL':
        ledger['krw_balance'] += (amount_krw - fee)
        ledger['positions'][coin_sym] = backup_pos - qty_coin
        if ledger['positions'].get(coin_sym,0.0) <= MIN_QTY:
            if coin_sym in ledger['positions']:
                del ledger['positions'][coin_sym]
        # record last sell timestamp per ticker for cooldown logic (canonical key)
        meta = ledger.setdefault('meta', {})
        meta.setdefault('REDACTED', {})[ticker] = timestamp
        # record last sell price for quick loss check
        meta[f'last_sell_price_{coin_sym}'] = exec_price

    new_krw = ledger['krw_balance']
    new_pos = ledger['positions'].get(coin_sym, 0.0)

    # 3. Create canonical entry
    entry = {
        'timestamp': timestamp,
        'side': side,
        'ticker': ticker,
        'exec_price_krw': exec_price,
        'qty_btc': qty_coin, # legacy key name for compatibility
        'amount_krw': amount_krw,
        'fee_krw': fee,
        'simulated': bool(SIMULATED),
        'source': 'auto_trader_v2'
    }
    entry['trade_id'] = _make_trade_id(entry)

    # 4. Append to history and save whole dict atomically
    ledger.setdefault('trade_history', []).append(entry)
    ledger.setdefault('meta', {})[f'last_{side.lower()}_ts'] = timestamp

    # 5. Retry / Rollback Logic
    max_retries = 3
    for attempt in range(max_retries):
        try:
            save_ledger(ledger)
            append_cron_log(f"[POST-TRADE SUCCESS] {side} {ticker} | KRW: {new_krw:,.0f} | {coin_sym}: {new_pos:.6f}")
            send_critical_alert(f"🟢 [TRADE SUCCESS] {side} {ticker} executed. \nPrice: {exec_price:,.0f} \nQty: {qty_coin:.6f}")
            return True
        except Exception as e:
            append_cron_log(f"Save attempt {attempt+1} failed: {e}")
            time.sleep(0.5)

    # ROLLBACK if all retries fail
    ledger['krw_balance'] = backup_krw
    if backup_pos > MIN_QTY:
        ledger['positions'][coin_sym] = backup_pos
    else:
        if coin_sym in ledger['positions']:
            del ledger['positions'][coin_sym]
    if ledger.get('trade_history'):
        ledger['trade_history'].pop() # remove failed entry

    msg = f"🔴 [CRITICAL ROLLBACK] {side} {ticker} failed to save after {max_retries} retries. Ledger state reverted."
    append_cron_log(msg)
    send_critical_alert(msg)
    return False

# --- Main Logic ---
def main():
    print('CRON_TRIGGERED',flush=True)
    append_cron_log('--- Cron Triggered: Multi-Strike Engine (LIVE) ---')
    # DEBUG: write quick heartbeat to debug log to trace startup/early exit
    try:
        with open('/Users/andy/.openclaw/workspace/auto_trader_debug.log','a') as df:
            df.write(f"START {datetime.now().isoformat()}\n")
    except Exception:
        pass
    ledger = load_ledger()
    try:
        with open('/Users/andy/.openclaw/workspace/auto_trader_debug.log','a') as df:
            df.write(f"LEDGER_LOADED krw={ledger.get('krw_balance')} positions={list(ledger.get('positions',{}).keys())} {datetime.now().isoformat()}\n")
    except Exception:
        pass

    for ticker in TARGET_TICKERS:
        coin_sym = ticker.split('-')[1]
        holding_qty = float(ledger.get('positions', {}).get(coin_sym, 0.0))
        krw_bal = float(ledger.get('krw_balance', 0.0))

        # DEBUG: loop entry
        try:
            with open('/Users/andy/.openclaw/workspace/auto_trader_debug.log','a') as df:
                df.write(f"LOOP_START {ticker} holding={holding_qty} krw={krw_bal} {datetime.now().isoformat()}\n")
        except Exception:
            pass

        snapshot = get_live_upbit_data(ticker)
        if not snapshot:
            append_cron_log(f"API Error for {ticker}. Skipping.")
            try:
                with open('/Users/andy/.openclaw/workspace/auto_trader_debug.log','a') as df:
                    df.write(f"API_ERROR {ticker} {datetime.now().isoformat()}\n")
            except Exception:
                pass
            continue

        current_price = snapshot['price']

        try:
            with open('/Users/andy/.openclaw/workspace/auto_trader_debug.log','a') as df:
                df.write(f"SNAPSHOT {ticker} price={current_price} rsi={snapshot.get('rsi')} {datetime.now().isoformat()}\n")
        except Exception:
            pass

        # [SELL LOGIC] - Evaluate if holding position
        if holding_qty > MIN_QTY:
            last_buy_price = current_price
            for trade in reversed(ledger.get('trade_history', [])):
                if trade['side'] == 'BUY' and trade.get('ticker', '') in (ticker, '') and trade.get('qty_btc', 0) > MIN_QTY:
                    last_buy_price = float(trade['exec_price_krw'])
                    break

            roi = (current_price - last_buy_price) / last_buy_price

            # Sell Conditions: Take Profit OR Stop Loss using configured thresholds
            if roi >= SELL_TP or roi <= SELL_SL:
                append_cron_log(f"SELL Triggered for {ticker}. ROI: {roi*100:.2f}% (TP {SELL_TP*100:.2f}% / SL {SELL_SL*100:.2f}%)")
                exec_price = current_price * (1 - SLIPPAGE)
                amount_krw = holding_qty * exec_price
                # perform sell
                success = execute_trade(ticker, 'SELL', amount_krw, holding_qty, exec_price, ledger)
                # mark last sell timestamp and enter temporary risk mode to avoid immediate re-entry
                try:
                    now_iso = datetime.now().isoformat()
                    meta = ledger.setdefault('meta', {})
                    last_sells = meta.setdefault('REDACTED', {})
                    last_sells[ticker] = now_iso
                    # risk mode minutes (short-term conservative window)
                    RISK_MODE_MIN = int(os.environ.get('RISK_MODE_MIN','10'))
                    risk = meta.setdefault('risk_mode', {})
                    risk[ticker] = (datetime.now() + timedelta(minutes=RISK_MODE_MIN)).isoformat()
                    save_ledger = None
                except Exception:
                    pass
                # ensure we do not evaluate BUY for this ticker in the same loop iteration
                continue
            else:
                append_cron_log(f"HOLD {ticker} | ROI: {roi*100:.2f}% | Waiting for target.")
                continue

        # [BUY LOGIC] - Evaluate funds and confidence (allow re-entry even if holding)
        if krw_bal > 10000:
            conf = compute_confidence(snapshot)
            # Cooldown: prevent rapid re-entry on same ticker — require last sell > COOLDOWN minutes ago or last buy global cooldown
            COOLDOWN_MIN = int(os.environ.get('REDACTED', '15'))
            allow_entry = True
            try:
                meta = ledger.setdefault('meta', {})
                # check per-ticker last sell
                last_sells = meta.get('REDACTED', {})
                last_sell_ts = last_sells.get(ticker)
                if last_sell_ts:
                    last_dt = datetime.fromisoformat(last_sell_ts)
                    if (datetime.now() - last_dt).total_seconds() < COOLDOWN_MIN*60:
                        allow_entry = False
                # check risk mode (if active, raise threshold)
                risk = meta.get('risk_mode', {})
                risk_until = risk.get(ticker)
                risk_active = False
                if risk_until:
                    try:
                        if datetime.fromisoformat(risk_until) > datetime.now():
                            risk_active = True
                    except Exception:
                        risk_active = False
            except Exception:
                allow_entry = True
            if not allow_entry:
                append_cron_log(f"SKIP BUY {ticker}: cooldown {COOLDOWN_MIN}m since last sell")
                continue
            # if in risk mode, require higher confidence
            effective_threshold = REDACTED
            if 'risk_active' in locals() and risk_active:
                effective_threshold = min(1.0, REDACTED + 0.10)
            if conf >= effective_threshold:
                append_cron_log(f"BUY Triggered for {ticker}! Conf: {conf:.3f} >= {effective_threshold}")
                # External aggregator check
                try:
                    if REDACTED and AGG_PATH.exists():
                        with open(AGG_PATH,'r') as af:
                            votes = json.load(af)
                        # votes is list of dicts with keys ts,ticker,winner
                        allowed=False
                        for v in votes:
                            if v.get('ticker')==ticker and v.get('winner')=='BUY':
                                allowed=True
                                break
                        if not allowed:
                            append_cron_log(f"SKIP BUY {ticker}: aggregator did not endorse BUY")
                            continue
                except Exception:
                    # on aggregator read errors, default to conservative skip
                    append_cron_log(f"SKIP BUY {ticker}: cannot read aggregator or error")
                    continue
                invest_krw = max(10000.0, krw_bal * 0.1)
                if invest_krw > krw_bal:
                    invest_krw = krw_bal

                exec_price = current_price * (1 + SLIPPAGE)
                qty_coin = invest_krw / exec_price

                # perform buy and update last_buy_ts
                success = execute_trade(ticker, 'BUY', invest_krw, qty_coin, exec_price, ledger)
                try:
                    if success:
                        ledger.setdefault('meta', {}).setdefault('REDACTED', {})[ticker] = datetime.now().isoformat()
                except Exception:
                    pass
            else:
                append_cron_log(f"Skip BUY {ticker}: Conf {conf:.3f} < {effective_threshold}")

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        msg = f'CRITICAL ERROR in main loop: {e}'
        append_cron_log(msg)
        send_critical_alert(msg)
