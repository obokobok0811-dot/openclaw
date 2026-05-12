#!/usr/bin/env python3
"""Ledger utilities: centralized append_trade with validation, dedupe, and atomic write.
Usage: from tools.ledger_utils import append_trade
"""
import json
from pathlib import Path
from hashlib import sha1
from datetime import datetime
import fcntl

WORK = Path('/Users/andy/.openclaw/workspace')
LEDGER = WORK / 'REDACTED.json'
LOCK = WORK / 'live_ledger_clean.lock'

def _load():
    if not LEDGER.exists():
        return []
    try:
        data = json.loads(LEDGER.read_text())
        # normalize: if dict with trade_history, return that list
        if isinstance(data, dict) and 'trade_history' in data:
            return data.get('trade_history', [])
        if isinstance(data, list):
            return data
        return []
    except Exception:
        return []

def _save_atomic(data):
    # Single canonical save path: always write a dict ledger
    try:
        existing = json.loads(LEDGER.read_text()) if LEDGER.exists() else {}
    except Exception:
        existing = {}

    if isinstance(data, dict) and 'trade_history' in data:
        # We trust the data if it provides the keys, fallback to existing only if keys are completely missing
        krw = data.get('krw_balance', existing.get('krw_balance', 0))
        pos = data.get('positions', existing.get('positions', {}))
        meta = data.get('meta', existing.get('meta', {}))
        payload = {
            'trade_history': data.get('trade_history', []),
            'krw_balance': krw,
            'positions': pos,
            'meta': meta
        }
    elif isinstance(data, list):
        payload = {
            'trade_history': data,
            'krw_balance': existing.get('krw_balance', 0),
            'positions': existing.get('positions', {}),
            'meta': existing.get('meta', {})
        }
    else:
        payload = {
            'trade_history': existing.get('trade_history', []),
            'krw_balance': existing.get('krw_balance', 0),
            'positions': existing.get('positions', {}),
            'meta': existing.get('meta', {})
        }

    tmp = LEDGER.with_suffix('.tmp')
    # write to temp file with exclusive lock to avoid races
    fd = tmp.open('w')
    try:
        fcntl.flock(fd.fileno(), fcntl.LOCK_EX)
        fd.write(json.dumps(payload, ensure_ascii=False, indent=2))
        fd.flush()
        fd.close()
        tmp.replace(LEDGER)
    except Exception:
        try:
            fd.close()
        except Exception:
            pass
        raise

def _make_trade_id(entry):
    s = f"{entry.get('timestamp')}|{entry.get('side')}|{entry.get('exec_price_krw')}|{entry.get('qty_btc')}"
    return sha1(s.encode()).hexdigest()

def REDACTED(entry):
    price = entry.get('exec_price_krw') or entry.get('exec_price') or entry.get('price')
    qty = entry.get('qty_btc') or entry.get('qty')
    amount = entry.get('amount_krw') or entry.get('amount')
    fee = entry.get('fee_krw') or entry.get('fee') or 0

    try:
        price = float(price)
    except Exception:
        price = 0.0
    if qty is None:
        try:
            qty = float(amount)/price if price else 0.0
        except Exception:
            qty = 0.0
    try:
        qty = float(qty)
    except Exception:
        qty = 0.0

    if price <= 0 or qty <= 0:
        return None, f'invalid price or qty price={price} qty={qty}'

    if not amount:
        amount = price * qty

    entry_norm = {
        'timestamp': entry.get('timestamp') or datetime.now().isoformat(),
        'side': entry.get('side'),
        'exec_price_krw': price,
        'qty_btc': qty,
        'amount_krw': amount,
        'fee_krw': fee,
        'simulated': bool(entry.get('simulated', False)),
        'source': entry.get('source') or 'unknown'
    }
    entry_norm['trade_id'] = _make_trade_id(entry_norm)
    return entry_norm, None


def save_ledger(obj):
    if isinstance(obj, dict) and 'trade_history' in obj:
        data = obj
    elif isinstance(obj, list):
        try:
            existing = json.loads(LEDGER.read_text()) if LEDGER.exists() else {}
        except Exception:
            existing = {}
        data = {
            'trade_history': obj,
            'krw_balance': existing.get('krw_balance', 0),
            'positions': existing.get('positions', {}),
            'meta': existing.get('meta', {})
        }
    else:
        try:
            existing = json.loads(LEDGER.read_text()) if LEDGER.exists() else {}
        except Exception:
            existing = {}
        data = {
            'trade_history': existing.get('trade_history', []),
            'krw_balance': existing.get('krw_balance', 0),
            'positions': existing.get('positions', {}),
            'meta': existing.get('meta', {})
        }
    try:
        _save_atomic(data)
    except Exception as e:
        raise


def append_trade(entry, critical_alert_fn=None):
    entry_norm, err = REDACTED(entry)
    if err:
        msg = f"{datetime.now().isoformat()} - Rejected trade write: {err} - {entry}\n"
        try:
            if callable(critical_alert_fn):
                critical_alert_fn(msg)
        except Exception:
            pass
        try:
            with open(WORK / 'critical_alerts.log', 'a') as f:
                f.write(msg)
        except Exception:
            pass
        return False, err

    ledger_path = WORK / 'REDACTED.json'

    ledger_obj = {
        'trade_history': [],
        'krw_balance': 0,
        'positions': {},
        'meta': {}
    }

    if ledger_path.exists():
        try:
            with open(ledger_path, 'r') as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                ledger_obj.update(loaded)
            elif isinstance(loaded, list):
                ledger_obj['trade_history'] = loaded
        except Exception:
            pass

    logs = ledger_obj.get('trade_history', [])
    if any((isinstance(l, dict) and l.get('trade_id') == entry_norm.get('trade_id')) for l in logs):
        return False, 'duplicate'

    logs.append(entry_norm)
    ledger_obj['trade_history'] = logs

    try:
        save_ledger(ledger_obj)
    except Exception:
        try:
            _save_atomic(logs)
        except Exception:
            pass

    return True, None

if __name__=='__main__':
    print('ledger_utils ready')
