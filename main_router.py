#!/usr/bin/env python3
"""Main Router: orchestrates regime check and weapons A/B/C across the trading day.

Behavior when executed (intended to be launched at 08:55 Mon-Fri by cron):
 - Enforces PID lock to prevent duplicate runs
 - 08:55: run regime_filter to compute Market_Regime (persisted to state/market_regime.json)
 - wait until 09:00, then start the appropriate weapon (A if BULL, B if BEAR) as a subprocess
 - at 15:30 run weapon_c_obsidian (end-of-day persistence)
 - clean up PID lock and exit

Note: this script assumes workspace path is /Users/andy/.openclaw/workspace and modules exist there.
"""
import os, sys, time, json, subprocess
from pathlib import Path
from datetime import datetime, time as dtime, timedelta

WORKDIR = Path(__file__).parent
STATE_DIR = WORKDIR / 'state'
PIDFILE = STATE_DIR / 'main_router.pid'
REGIME_FILE = STATE_DIR / 'market_regime.json'

# --- PID lock ---
def is_running(pid):
    try:
        os.kill(pid, 0)
        return True
    except Exception:
        return False

if PIDFILE.exists():
    try:
        existing = int(PIDFILE.read_text().strip())
        if is_running(existing):
            print('main_router: another instance is running (pid=', existing, ') - exiting')
            sys.exit(0)
        else:
            PIDFILE.unlink()
    except Exception:
        try:
            PIDFILE.unlink()
        except Exception:
            pass

STATE_DIR.mkdir(parents=True, exist_ok=True)
PIDFILE.write_text(str(os.getpid()))

try:
    print('main_router: started, pid=', os.getpid())
    # 08:55 step: run regime filter
    print('main_router: running regime_filter (08:55 step)')
    subprocess.run([sys.executable, str(WORKDIR / 'regime_filter.py')], check=False)
    # read regime and series for ATR
    regime = None
    quadrant = None
    sma60 = None
    if REGIME_FILE.exists():
        try:
            j = json.loads(REGIME_FILE.read_text())
            regime = j.get('market_regime')
            sma60 = j.get('sma60')
            print('main_router: regime read:', regime)
        except Exception:
            regime = None
    else:
        print('main_router: regime file not found')

    # compute ATR from saved series if present
    series_file = STATE_DIR / '005930_series.json'
    atr_current = None
    atr20_mean = None
    if series_file.exists():
        try:
            s = json.loads(series_file.read_text())
            closes = s.get('closes',[])
            highs = s.get('highs',[])
            lows = s.get('lows',[])
            # compute True Range series
            trs = []
            for i in range(1, len(closes)):
                tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
                trs.append(tr)
            # ATR series (14) simple moving average over TRs
            atrs = []
            period = 14
            for i in range(len(trs)):
                if i+1 >= period:
                    atrs.append(sum(trs[i+1-period:i+1]) / period)
                else:
                    atrs.append(None)
            # current ATR is last non-None
            atr_values = [a for a in atrs if a is not None]
            if atr_values:
                atr_current = atr_values[-1]
                # 20-day mean of ATR (use last 20 atr_values)
                if len(atr_values) >= 20:
                    atr20_mean = sum(atr_values[-20:]) / 20.0
                else:
                    atr20_mean = sum(atr_values) / len(atr_values)
        except Exception:
            pass
    # determine quadrant based on sma60 and atr comparison
    if regime and atr_current is not None and atr20_mean is not None:
        trend_up = (j.get('current') > sma60)
        vol_high = (atr_current > atr20_mean)
        if trend_up and not vol_high:
            quadrant = 1  # Goldilocks
        elif trend_up and vol_high:
            quadrant = 2  # Bull-Trap Risk
        elif (not trend_up) and not vol_high:
            quadrant = 3  # Bleeding
        else:
            quadrant = 4  # Chaos
        print(f'main_router: quadrant {quadrant} determined (atr_current={atr_current}, atr20_mean={atr20_mean})')
    else:
        print('main_router: insufficient data for quadrant determination; defaulting to regime-based switch')

    # wait until 09:00 local time (if script started at 08:55 via cron, this will sleep ~5 minutes)
    now = datetime.now()
    target = datetime.combine(now.date(), dtime(hour=9, minute=0))
    if now > target:
        # already past 09:00 today; proceed immediately
        pass
    else:
        delta = (target - now).total_seconds()
        print(f'main_router: sleeping {int(delta)}s until 09:00 to start trading module')
        time.sleep(delta)

    # 09:00 step: start weapon A or B with weights per quadrant
    wa = WORKDIR / 'weapon_a_swing.py'
    wb = WORKDIR / 'weapon_b_daytrade.py'
    weights = {'weapon_a':0.0, 'weapon_b':0.0}
    if quadrant == 1:
        weights = {'weapon_a':1.0, 'weapon_b':0.0}
    elif quadrant == 2:
        weights = {'weapon_a':0.5, 'weapon_b':0.5}
    elif quadrant == 3:
        weights = {'weapon_a':0.0, 'weapon_b':0.0}
    elif quadrant == 4:
        weights = {'weapon_a':0.0, 'weapon_b':1.0}
    # pass weights via environment for called modules
    env = os.environ.copy()
    env['WEIGHT_A'] = str(weights['weapon_a'])
    env['WEIGHT_B'] = str(weights['weapon_b'])
    print('main_router: weights set', weights)
    if weights['weapon_a'] > 0:
        print('main_router: launching weapon_a_swing')
        subprocess.run([sys.executable, str(wa)], env=env, check=False)
    if weights['weapon_b'] > 0:
        print('main_router: launching weapon_b_daytrade')
        subprocess.run([sys.executable, str(wb)], env=env, check=False)
    if weights['weapon_a']==0 and weights['weapon_b']==0:
        print('main_router: no trading weapons scheduled (quadrant3 or unknown)')

    # wait until 15:30 for EOD processing
    now = datetime.now()
    target_eod = datetime.combine(now.date(), dtime(hour=15, minute=30))
    if now > target_eod:
        # already past EOD; run immediately
        pass
    else:
        delta = (target_eod - now).total_seconds()
        print(f'main_router: sleeping {int(delta)}s until 15:30 for EOD tasks')
        time.sleep(delta)

    # 15:30 step: run weapon_c_obsidian to persist end-of-day notes
    print('main_router: running weapon_c_obsidian (EOD)')
    subprocess.run([sys.executable, str(WORKDIR / 'weapon_c_obsidian.py')], check=False)

    print('main_router: completed all scheduled steps for today')
finally:
    try:
        if PIDFILE.exists():
            PIDFILE.unlink()
    except Exception:
        pass

# --- Crontab instruction (user must copy/paste into their terminal) ---
CRON_LINE = "55 8 * * 1-5 /usr/bin/python3 /Users/andy/.openclaw/workspace/main_router.py >> /Users/andy/.openclaw/workspace/state/main_router.log 2>&1 &"

if __name__ == '__main__':
    print('\nTo enable automatic runs add this crontab line (run: crontab -e):')
    print(CRON_LINE)
