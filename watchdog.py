#!/usr/bin/env python3
import time, os, subprocess, shutil
from pathlib import Path
BASE=Path('/Users/andy/.openclaw/workspace')
PRICE_FILE=BASE/'holden_live_price.json'
AUTO=BASE/'run_auto_trader.sh'
BACKUP_DIR=BASE/'ops'/'pre_restart_backups'
BACKUP_DIR.mkdir(parents=True, exist_ok=True)
RESTART_LIMIT=3
WINDOW_SEC=1800

def mtime(path):
    try:
        return path.stat().st_mtime
    except Exception:
        return 0

history=[]

while True:
    now=time.time()
    mt=mtime(PRICE_FILE)
    stale=(now-mt)>90  # stale threshold 90s
    if stale:
        # rate limit restarts
        history=[t for t in history if now-t<WINDOW_SEC]
        if len(history)>=RESTART_LIMIT:
            print('Restart rate limit reached, skipping')
        else:
            # pre-restart backup
            ts=time.strftime('%Y%m%dT%H%M%S')
            try:
                if PRICE_FILE.exists():
                    dst=BACKUP_DIR/f'holden_live_price.json.pre_restart.{ts}.bak'
                    shutil.copy2(PRICE_FILE, dst)
                # delay before actual restart to allow transients
                time.sleep(60)
                # recheck
                if (time.time()-mtime(PRICE_FILE))>90:
                    history.append(now)
                    # run restart script
                    if AUTO.exists():
                        subprocess.Popen([str(AUTO)])
                    else:
                        print('Auto script missing')
            except Exception as e:
                print('watchdog backup/restart failed',e)
    time.sleep(30)
