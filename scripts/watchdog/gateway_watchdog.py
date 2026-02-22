#!/usr/bin/env python3
"""
Gateway Watchdog: 주기적 헬스체크 + 자동 재시작 + Telegram 알림
LaunchAgent로 5분마다 실행
"""
import subprocess
import json
import time
import urllib.request
import urllib.parse
from pathlib import Path
from datetime import datetime

# Config
MAX_RESTART_ATTEMPTS = 3
STATE_FILE = Path(__file__).parent / 'watchdog_state.json'
TELEGRAM_BOT_TOKEN = None
TELEGRAM_CHAT_ID = '5510621427'
CRED_FILE = Path(__file__).parent.parent.parent / 'credentials' / 'telegram_bot.json'

def load_telegram_token():
    global TELEGRAM_BOT_TOKEN
    try:
        with open(CRED_FILE) as f:
            data = json.load(f)
            TELEGRAM_BOT_TOKEN = data.get('bot_token')
    except Exception:
        pass

def send_telegram(msg):
    if not TELEGRAM_BOT_TOKEN:
        return
    try:
        url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
        data = urllib.parse.urlencode({
            'chat_id': TELEGRAM_CHAT_ID,
            'text': msg,
            'parse_mode': 'HTML'
        }).encode()
        req = urllib.request.Request(url, data=data)
        urllib.request.urlopen(req, timeout=15)
    except Exception as e:
        print(f'Telegram send failed: {e}')

def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {'consecutive_failures': 0, 'restart_attempts': 0, 'last_healthy': None, 'last_failure': None}

def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

def check_gateway_health():
    """Check if gateway is responding."""
    try:
        result = subprocess.run(
            ['openclaw', 'gateway', 'status'],
            capture_output=True, text=True, timeout=30
        )
        output = result.stdout.lower() + result.stderr.lower()
        # Gateway is healthy if status returns 0 and contains 'running' or similar
        if result.returncode == 0 and ('running' in output or 'online' in output or 'ok' in output):
            return True, result.stdout.strip()
        return False, result.stdout.strip() + result.stderr.strip()
    except subprocess.TimeoutExpired:
        return False, 'timeout'
    except Exception as e:
        return False, str(e)

def restart_gateway():
    """Attempt to restart the gateway."""
    try:
        result = subprocess.run(
            ['openclaw', 'gateway', 'restart'],
            capture_output=True, text=True, timeout=60
        )
        return result.returncode == 0, result.stdout.strip() + result.stderr.strip()
    except subprocess.TimeoutExpired:
        return False, 'restart timeout'
    except Exception as e:
        return False, str(e)

def main():
    load_telegram_token()
    state = load_state()
    now = datetime.now().isoformat()

    healthy, detail = check_gateway_health()

    if healthy:
        # Reset failure counters on healthy check
        if state['consecutive_failures'] > 0:
            send_telegram(f'✅ Gateway 복구 완료\n시각: {now}\n이전 실패 횟수: {state["consecutive_failures"]}')
        state['consecutive_failures'] = 0
        state['restart_attempts'] = 0
        state['last_healthy'] = now
        save_state(state)
        print(f'[{now}] OK: {detail}')
        return

    # Failure detected
    state['consecutive_failures'] += 1
    state['last_failure'] = now
    print(f'[{now}] FAIL ({state["consecutive_failures"]}): {detail}')

    if state['restart_attempts'] >= MAX_RESTART_ATTEMPTS:
        # Already tried max times, just alert
        if state['consecutive_failures'] % 12 == 1:  # Re-alert every hour (12 * 5min)
            send_telegram(
                f'🚨 Gateway 장기 장애\n'
                f'시각: {now}\n'
                f'연속 실패: {state["consecutive_failures"]}회\n'
                f'재시작 시도 {MAX_RESTART_ATTEMPTS}회 모두 실패\n'
                f'수동 개입 필요:\n'
                f'<code>openclaw gateway restart</code>'
            )
        save_state(state)
        return

    # Attempt restart
    state['restart_attempts'] += 1
    attempt = state['restart_attempts']
    print(f'[{now}] Attempting restart ({attempt}/{MAX_RESTART_ATTEMPTS})...')

    success, restart_detail = restart_gateway()

    if success:
        # Wait a bit and verify
        time.sleep(5)
        healthy2, detail2 = check_gateway_health()
        if healthy2:
            send_telegram(
                f'🔄 Gateway 자동 재시작 성공\n'
                f'시각: {now}\n'
                f'시도 횟수: {attempt}/{MAX_RESTART_ATTEMPTS}'
            )
            state['consecutive_failures'] = 0
            state['restart_attempts'] = 0
            state['last_healthy'] = datetime.now().isoformat()
            save_state(state)
            return

    # Restart failed or gateway still unhealthy
    send_telegram(
        f'⚠️ Gateway 재시작 시도 ({attempt}/{MAX_RESTART_ATTEMPTS})\n'
        f'시각: {now}\n'
        f'결과: {"성공했으나 여전히 비정상" if success else "실패"}\n'
        f'상세: {restart_detail[:200]}'
    )
    save_state(state)

if __name__ == '__main__':
    main()
