#!/usr/bin/env python3
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
# Adjusted default for new weighting (momentum-heavy)
REDACTED = float(os.environ.get('REDACTED', '0.35'))
# Candidate A defaults: TP 2%, SL -1%
SELL_TP = float(os.environ.get('SELL_TP', '0.05'))
SELL_SL = float(os.environ.get('SELL_SL', '-0.03'))
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
    backoff = 0.5
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            # increased timeout to 8s to tolerate slower responses
            with urllib.request.urlopen(req, timeout=8) as response:
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
        except Exception as e:
            append_cron_log(f"Upbit API attempt {attempt+1} failed for {market}: {e}")
            time.sleep(backoff)
            backoff = min(backoff * 2, 4)
    return None


def compute_confidence(snapshot):
    """Compute confidence using RSI and EMA momentum with adjusted weights.
    RSI weight = 0.3, Momentum weight = 0.7. Apply penalty when strong downtrend present.
    """
    if not snapshot:
        return 0.0
    price = snapshot['price']
    ema5, ema20, rsi = snapshot['ema5'], snapshot['ema20'], snapshot['rsi']

    # RSI contribution
    rsi_score = max(0.0, min(1.0, abs(rsi - 50.0) / 50.0))

    # Momentum contribution (scaled then mapped to 0..1)
    momentum = (ema5 - ema20) / price if price > 0 else 0.0
    momentum_score = max(-1.0, min(1.0, momentum * 10.0))
    momentum_score = (momentum_score + 1.0) / 2.0

    # raw_momentum penalty threshold
    REDACTED = -0.01
    if momentum < REDACTED:
        momentum_score *= 0.4

    # weighted combine: momentum heavier
    rsi_w = 0.3
    mom_w = 0.7
    conf = rsi_w * rsi_score + mom_w * momentum_score
    return max(0.0, min(1.0, conf))

# --- RAG check: query Obsidian index for similar past conditions and penalize/conflict ---
import subprocess

def REDACTED(ticker, rsi, snapshot):
    """Query obsidian index via obsidian_search and inspect matched files for consecutive loss patterns.
    Returns penalty multiplier (<=1.0) and reason string.
    """
    try:
        script = '/Users/andy/.openclaw/workspace/tools/obsidian_search.py'
        query = f"{ticker} BUY"
        # call search without show, parse output lines
        p = subprocess.run(['/usr/bin/python3', script, '--query', query], capture_output=True, text=True, timeout=10)
        out = p.stdout
        if 'No matches' in out:
            return 1.0, ''
        # parse file lines: each line contains date,file,...
        loss_count = 0
        total_checked = 0
        for line in out.splitlines():
            parts = line.split()
            if len(parts) < 1:
                continue
            # try to robustly find a date token and a filename token ending with .md
            date = None
            fname_token = None
            for tok in parts:
                if __import__('re').match(r"^\d{4}-\d{2}-\d{2}$", tok):
                    date = tok
                if tok.endswith('.md'):
                    fname_token = tok
            # fallback: try regex capture of date+path
            if not date or not fname_token:
                m = __import__('re').search(r"(\d{4}-\d{2}-\d{2}).*?(\S+\.md)", line)
                if m:
                    date = m.group(1)
                    fname_token = m.group(2)
            if not date or not fname_token:
                # unable to parse this line
                continue
            # normalize filename to basename
            fname_basename = Path(fname_token).name
            # construct expected session file path under Sessions/<date>/<basename>
            path = Path('/Users/andy/Documents/Obsidian/Obsidian Vault/OpenClaw/Sessions')/date/fname_basename
            text = None
            if not path.exists():
                # try archive fallback
                tar = Path('/Users/andy/.openclaw/workspace/ops/ob_archive_v2')/f'ob_{date}.tar.gz'
                if tar.exists():
                    try:
                        import tarfile
                        with tarfile.open(tar) as tf:
                            member = f"{date}/{fname_basename}"
                            try:
                                f = tf.extractfile(member)
                                text = f.read().decode()
                            except Exception:
                                text = None
                    except Exception:
                        text = None
                # if still not found, try direct path as provided by token (may include relative subdir)
                if text is None:
                    possible = Path('/Users/andy/Documents/Obsidian/Obsidian Vault/OpenClaw')/fname_token
                    if possible.exists():
                        text = possible.read_text()
            else:
                text = path.read_text()
            if not text:
                continue
            total_checked += 1
            # heuristic: look for SELL losses or negative P/L patterns
            # count occurrences of 'LOSS' or 'PL' or negative numbers; treat any hit as evidence
            negs = len(__import__('re').findall(r'\bPL\b|loss|\b-\d{1,}', text, flags=__import__('re').IGNORECASE))
            # consider a file showing at least one negative/LOSS mention as a loss case
            if negs >= 1:
                loss_count += 1
        # decide penalty: if many matching files show repeated losses, reduce confidence
        if total_checked==0:
            return 1.0, ''
        frac = loss_count/total_checked
        if frac >= 0.5:
            return 0.5, f'Penalty applied: {loss_count}/{total_checked} similar historical loss cases'
        elif frac > 0:
            return 0.8, f'Minor penalty: {loss_count}/{total_checked} similar loss cases'
        else:
            return 1.0, ''
    except Exception as e:
        return 1.0, ''

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

    # Step 3: Load Market_Brief to adjust max position sizing per ticker
    market_brief_dir = Path('/Users/andy/Documents/Obsidian/Obsidian Vault/OpenClaw/Market_Brief')
    max_position_map = {}
    try:
        # Load Market_Brief: ignore README.md and prefer YYYY-MM-DD.md by date in filename; fall back to mtime.
        briefs = [p for p in market_brief_dir.glob('*.md') if not p.name.lower().startswith('readme')]
        # prefer files named YYYY-MM-DD.md
        import re as _re
        date_named = []
        other = []
        for p in briefs:
            m = _re.match(r'^(\d{4}-\d{2}-\d{2})\.md$', p.name)
            if m:
                try:
                    dt = datetime.fromisoformat(m.group(1))
                    date_named.append((dt, p))
                except Exception:
                    other.append(p)
            else:
                other.append(p)
        latest = None
        if date_named:
            # pick the newest date by filename; if multiple, use mtime to break ties
            date_named.sort(key=lambda x: (x[0], x[1].stat().st_mtime))
            latest = date_named[-1][1]
        elif briefs:
            # fallback: pick most recently modified
            briefs.sort(key=lambda x: x.stat().st_mtime)
            latest = briefs[-1]
        if latest:
            try:
                txt = latest.read_text()
                m = _re.search(r"---\n(.*?)\n---", txt, flags=_re.DOTALL)
                if m:
                    try:
                        import yaml as _yaml
                        meta = _yaml.safe_load(m.group(1))
                        if isinstance(meta, dict) and 'max_position' in meta:
                            max_position_map = meta.get('max_position', {})
                    except Exception:
                        max_position_map = {}
                with open('/Users/andy/.openclaw/workspace/auto_trader_debug.log','a') as df:
                    df.write(f"MARKET_BRIEF_LOADED {latest.name} map={max_position_map} {datetime.now().isoformat()}\n")
            except Exception:
                pass
    except Exception:
        pass

    for ticker in TARGET_TICKERS:
        coin_sym = ticker.split('-')[1]
        holding_qty = float(ledger.get('positions', {}).get(coin_sym, 0.0))
        krw_bal = float(ledger.get('krw_balance', 0.0))

        # adjust max invest fraction from market brief if present
        try:
            max_frac = float(max_position_map.get(ticker, max_position_map.get(coin_sym, None))) if max_position_map else None
        except Exception:
            max_frac = None
        if max_frac is not None:
            # set per-ticker invest cap via environment override for this run
            per_ticker_cap = max_frac
        else:
            per_ticker_cap = 0.1  # default 10% of KRW balance

        # DEBUG: loop entry
        try:
            with open('/Users/andy/.openclaw/workspace/auto_trader_debug.log','a') as df:
                df.write(f"LOOP_START {ticker} holding={holding_qty} krw={krw_bal} per_ticker_cap={per_ticker_cap} {datetime.now().isoformat()}\n")
        except Exception:
            pass

        # Before snapshot loop starts, load Market_Brief once per run (done earlier in outer loop)
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

        # compute rsi_prev from snapshot history if available
        rsi_prev = None
        try:
            history = snapshot.get('history_prices', [])
            if len(history) > 15:
                # compute previous RSI using prices excluding last entry
                def compute_rsi(prices, period=14):
                    if len(prices) < period + 1:
                        return None
                    gains=[]; losses=[]
                    for i in range(1, period+1):
                        d = prices[-i-1] - prices[-i-2]
                        if d>0:
                            gains.append(d); losses.append(0)
                        else:
                            gains.append(0); losses.append(-d)
                    avg_gain=sum(gains)/period
                    avg_loss=sum(losses)/period
                    if avg_loss==0:
                        return 100.0
                    rs = avg_gain/avg_loss
                    return 100 - (100/(1+rs))
                rsi_prev = compute_rsi(history[:-1])
        except Exception:
            rsi_prev = None

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
            # compute confidence based on snapshot (uses EMA/RSI)
            conf = compute_confidence(snapshot)
            # Cooldown: prevent rapid re-entry on same ticker — require last sell > COOLDOWN minutes ago or last buy global cooldown
            COOLDOWN_MIN = int(os.environ.get('REDACTED', '15'))
            allow_entry = True
            # Enforce new buy rule: require bounce from oversold (rsi_prev <=25 and rsi > rsi_prev)
            rsi_now = snapshot.get('rsi')
            if rsi_prev is None or not (rsi_prev <= 25 and rsi_now is not None and rsi_now > rsi_prev):
                append_cron_log(f"SKIP BUY {ticker}: no confirmed oversold bounce (rsi_prev={rsi_prev} rsi_now={rsi_now})")
                continue
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
                # RAG check: consult past records for similar losing patterns
                penalty_mul, reason = REDACTED(ticker, snapshot.get('rsi'), snapshot)
                if penalty_mul < 1.0:
                    old_conf = conf
                    conf = conf * penalty_mul
                    append_cron_log(f"RAG penalty applied for {ticker}: {reason} conf {old_conf:.3f}->{conf:.3f}")
                if conf < effective_threshold:
                    append_cron_log(f"After RAG penalty, Skip BUY {ticker}: Conf {conf:.3f} < {effective_threshold}")
                    continue

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
                        # write Obsidian MD with YAML frontmatter for Dataview
                        try:
                            day_dir = Path('/Users/andy/Documents/Obsidian/Obsidian Vault/OpenClaw/Sessions')/datetime.datetime.now().strftime('%Y-%m-%d')
                            day_dir.mkdir(parents=True, exist_ok=True)
                            md = day_dir / f"trade_buy_{int(time.time())}.md"
                            yaml = {
                                'ticker': ticker,
                                'side': 'BUY',
                                'price': int(exec_price),
                                'qty': qty_coin,
                                'profit': None,
                                'rsi': snapshot.get('rsi'),
                                'confidence': round(conf,6),
                                'timestamp': datetime.datetime.now().isoformat()
                            }
                            with md.open('w') as mf:
                                mf.write('---\n')
                                for k,v in yaml.items():
                                    mf.write(f"{k}: {v}\n")
                                mf.write('---\n\n')
                                mf.write(f"# Trade BUY {ticker}\n\n")
                                mf.write(f"Executed at {yaml['timestamp']}\n")
                        except Exception:
                            pass
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
        # Step 4: Self-Healing - consult error playbooks in Obsidian and attempt recovery commands
        try:
            playbook_dir = Path('/Users/andy/Documents/Obsidian/Obsidian Vault/OpenClaw')
            # search for files with #error_playbook tag
            candidates = []
            for p in playbook_dir.rglob('*.md'):
                try:
                    t = p.read_text()
                    if '#error_playbook' in t:
                        candidates.append(p)
                except Exception:
                    continue
            for pb in candidates:
                txt = pb.read_text()
                # find code blocks or lines prefixed with CMD:
                import re
                cmds = re.findall(r'^(?:CMD:|```bash\n)(.+?)(?:\n```|$)', txt, flags=re.DOTALL | re.MULTILINE)
                # also find explicit lines like $ pkill -f openclaw
                more = re.findall(r'^\$\s*(.+)$', txt, flags=re.MULTILINE)
                for c in more:
                    cmds.append(c)
                # Prepare Allowlist: only permit safe patterns. Patterns are anchored regexes.
                ALLOWLIST_PATTERNS = [
                    r'^pkill\b',                # allow pkill with safe usage
                    r'^echo\b',                 # echo for simple outputs
                    r'^/usr/bin/\w+/restart_\w+\.sh$',  # allow specific restart scripts by absolute path
                    r'^/bin/sh\s+/Users/andy/.openclaw/workspace/scripts/.*',
                    r'^systemctl\s+(restart|status)\b', # allow service restart/status (careful)
                ]
                unsafe_commands = []
                import re as _re
                for cmd in cmds:
                    c = cmd.strip()
                    append_cron_log(f"PLAYBOOK_PARSE {pb.name} -> {c}")
                    allowed = False
                    for pat in ALLOWLIST_PATTERNS:
                        try:
                            if _re.search(pat, c):
                                allowed = True
                                break
                        except Exception:
                            continue
                    # extra safety: disallow dangerous tokens regardless of pattern
                    dangerous_tokens = [' rm ', ' rm-', 'chmod ', 'chown ', 'sudo ', 'passwd', 'mkfs', 'dd ', ':(){', 'shutdown', 'reboot']
                    if any(tok in (' ' + c + ' ') for tok in dangerous_tokens):
                        allowed = False
                    if allowed:
                        append_cron_log(f"PLAYBOOK_ALLOWED {pb.name} -> {c}")
                        if not SIMULATED:
                            try:
                                subprocess.run(c, shell=True, timeout=30)
                                append_cron_log(f"PLAYBOOK_RAN {pb.name} -> {c}")
                            except Exception as ee:
                                append_cron_log(f"PLAYBOOK_CMD_FAIL {c} -> {ee}")
                        else:
                            append_cron_log(f"SIMULATED_EXEC: {c}")
                    else:
                        append_cron_log(f"PLAYBOOK_BLOCKED {pb.name} -> {c}")
                        unsafe_commands.append(c)
                if unsafe_commands:
                    append_cron_log(f"REDACTED {pb.name} count={len(unsafe_commands)} cmds={unsafe_commands}")
        except Exception as ee:
            append_cron_log(f"REDACTED -> {ee}")
