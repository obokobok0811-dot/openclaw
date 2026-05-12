#!/usr/bin/env python3
"""OpenClaw auto-updater: check for new version, install, restart gateway."""

import json
import subprocess
import sys
import os
import urllib.request
from pathlib import Path
from datetime import datetime

STATE_FILE = Path(__file__).parent / "update_state.json"
LOG_FILE = Path(__file__).parent / "auto_update.log"

TELEGRAM_BOT_TOKEN = None
TELEGRAM_CHAT_ID = "5510621427"

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def get_current_version():
    try:
        r = subprocess.run(["openclaw", "--version"], capture_output=True, text=True, timeout=10)
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception:
        return None

def get_latest_version():
    try:
        req = urllib.request.Request("https://registry.npmjs.org/openclaw/latest")
        req.add_header("Accept", "application/json")
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            return data.get("version")
    except Exception as e:
        log(f"npm registry check failed: {e}")
        return None

def load_bot_token():
    global TELEGRAM_BOT_TOKEN
    cred_path = Path(__file__).parent.parent.parent / "credentials" / "telegram_bot.json"
    if cred_path.exists():
        with open(cred_path) as f:
            data = json.load(f)
            TELEGRAM_BOT_TOKEN = data.get("token") or data.get("bot_token")

def send_telegram(msg):
    if not TELEGRAM_BOT_TOKEN:
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = json.dumps({"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"}).encode()
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        log(f"Telegram send failed: {e}")

def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def do_update(current, latest):
    log(f"Updating openclaw: {current} → {latest}")

    # Step 1: npm install
    r = subprocess.run(
        ["sudo", "-n", "npm", "i", "-g", "openclaw@latest"],
        capture_output=True, text=True, timeout=120
    )

    if r.returncode != 0:
        log(f"npm install failed (exit {r.returncode}): {r.stderr[-500:]}")
        send_telegram(f"⚠️ OpenClaw 자동 업데이트 실패\n{current} → {latest}\n\n{r.stderr[-300:]}")
        return False

    # Verify
    new_ver = get_current_version()
    if not new_ver or new_ver == current:
        log(f"Version unchanged after install: {new_ver}")
        send_telegram(f"⚠️ OpenClaw 업데이트 설치 후 버전 미변경: {new_ver}")
        return False

    log(f"Installed: {new_ver}")

    # Step 2: restart gateway
    try:
        r2 = subprocess.run(
            ["openclaw", "gateway", "restart"],
            capture_output=True, text=True, timeout=30
        )
        if r2.returncode == 0:
            log("Gateway restarted")
        else:
            log(f"Gateway restart failed: {r2.stderr}")
    except Exception as e:
        log(f"Gateway restart error: {e}")

    send_telegram(f"✅ OpenClaw 자동 업데이트 완료\n{current} → {new_ver}\n게이트웨이 재시작됨 🦞")
    return True

def main():
    load_bot_token()
    current = get_current_version()
    latest = get_latest_version()

    if not current or not latest:
        log(f"Version check failed: current={current}, latest={latest}")
        return

    if current == latest:
        log(f"Up to date: {current}")
        return

    log(f"New version available: {current} → {latest}")

    state = load_state()
    last_failed = state.get("last_failed_version")

    # Don't retry same failed version more than 3 times
    fail_count = state.get("fail_count", 0)
    if last_failed == latest and fail_count >= 3:
        log(f"Skipping {latest}: failed {fail_count} times already")
        return

    success = do_update(current, latest)

    if success:
        state["last_updated"] = latest
        state["last_updated_at"] = datetime.now().isoformat()
        state.pop("last_failed_version", None)
        state.pop("fail_count", None)
    else:
        state["last_failed_version"] = latest
        state["fail_count"] = fail_count + 1

    save_state(state)

if __name__ == "__main__":
    main()
