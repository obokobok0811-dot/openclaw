#!/usr/bin/env python3
"""
OpenClaw 야간 업데이트 체커.
매일 21:00 KST 실행. 새 버전 있으면 changelog 요약을 Telegram으로 전송.
없으면 무음.
"""
import json, subprocess, sys, urllib.request, urllib.error, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
STATE_FILE = Path(__file__).resolve().parent / 'update_state.json'
CRED_FILE = ROOT / 'credentials' / 'telegram_bot.json'
CHAT_ID = '5510621427'

CHANGELOG_URL = 'https://raw.githubusercontent.com/openclaw/openclaw/main/CHANGELOG.md'
NPM_URL = 'https://registry.npmjs.org/openclaw/latest'


def get_current_version():
    """Get locally installed OpenClaw version."""
    try:
        result = subprocess.run(['openclaw', '--version'], capture_output=True, text=True, timeout=10)
        return result.stdout.strip()
    except Exception:
        return None


def get_latest_version():
    """Get latest version from npm registry."""
    try:
        req = urllib.request.Request(NPM_URL)
        resp = urllib.request.urlopen(req, timeout=15)
        data = json.loads(resp.read())
        return data.get('version')
    except Exception as e:
        print(f'WARN: npm check failed: {e}', flush=True)
        return None


def get_last_notified():
    """Get last version we notified about."""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE) as f:
                return json.load(f).get('last_notified')
        except Exception:
            pass
    return None


def save_notified(version):
    """Save the version we just notified about."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump({'last_notified': version}, f)


def fetch_changelog():
    """Fetch CHANGELOG.md from GitHub."""
    try:
        req = urllib.request.Request(CHANGELOG_URL)
        resp = urllib.request.urlopen(req, timeout=15)
        return resp.read().decode('utf-8')
    except Exception as e:
        print(f'WARN: changelog fetch failed: {e}', flush=True)
        return None


def extract_version_section(changelog, version):
    """Extract the section for a specific version from changelog."""
    lines = changelog.split('\n')
    in_section = False
    section = []
    # Match ## version or ## version (date)
    version_pattern = re.compile(rf'^##\s+{re.escape(version)}')
    next_version = re.compile(r'^##\s+\d{4}\.')

    for line in lines:
        if version_pattern.search(line):
            in_section = True
            section.append(line)
            continue
        if in_section:
            if next_version.search(line) and not version_pattern.search(line):
                break
            section.append(line)

    return '\n'.join(section).strip() if section else None


def format_telegram_message(current, latest, section):
    """Format changelog section into clean Telegram message."""
    msg = f"🆕 <b>OpenClaw 업데이트 발견</b>\n"
    msg += f"현재: <code>{current}</code> → 최신: <code>{latest}</code>\n\n"

    if not section:
        msg += "변경사항을 가져올 수 없습니다.\n"
        msg += f"https://github.com/openclaw/openclaw/releases"
        return msg

    # Parse section into categories
    categories = {}
    current_cat = None
    for line in section.split('\n'):
        line = line.strip()
        if line.startswith('### '):
            current_cat = line[4:].strip()
            categories[current_cat] = []
        elif line.startswith('- ') and current_cat:
            # Clean up: shorten long entries, remove PR links
            entry = line[2:].strip()
            # Remove (#nnnnn) PR references
            entry = re.sub(r'\s*\(#\d+\)', '', entry)
            # Remove Thanks @user
            entry = re.sub(r'\s*Thanks @\S+\.?', '', entry)
            # Truncate long entries
            if len(entry) > 120:
                entry = entry[:117] + '...'
            categories[current_cat].append(entry)

    # Category emoji map
    emoji_map = {
        'Changes': '✨',
        'Breaking': '🔴',
        'Fixes': '🔧',
        'Security': '🔒',
        'New': '🆕',
    }

    for cat, items in categories.items():
        if not items:
            continue
        emoji = '📋'
        for key, em in emoji_map.items():
            if key.lower() in cat.lower():
                emoji = em
                break

        msg += f"{emoji} <b>{cat}</b>\n"
        # Show max 8 items per category, summarize rest
        shown = items[:8]
        for item in shown:
            msg += f"  • {item}\n"
        if len(items) > 8:
            msg += f"  <i>...외 {len(items) - 8}건</i>\n"
        msg += "\n"

    msg += f"업데이트: <code>openclaw update</code>"
    return msg


def send_telegram(text):
    """Send message to Telegram."""
    try:
        with open(CRED_FILE) as f:
            cred = json.load(f)
        bot_token = cred.get('bot_token', cred.get('token', ''))
        if not bot_token:
            print('WARN: No bot token', flush=True)
            return False

        data = json.dumps({
            'chat_id': CHAT_ID,
            'text': text,
            'parse_mode': 'HTML',
            'disable_web_page_preview': True,
        }).encode()

        req = urllib.request.Request(
            f'https://api.telegram.org/bot{bot_token}/sendMessage',
            data=data,
            headers={'Content-Type': 'application/json'},
        )
        urllib.request.urlopen(req, timeout=15)
        return True
    except Exception as e:
        print(f'WARN: Telegram send failed: {e}', flush=True)
        return False


def main():
    current = get_current_version()
    latest = get_latest_version()

    if not current or not latest:
        print(f'Could not determine versions (current={current}, latest={latest})', flush=True)
        return

    print(f'Current: {current}, Latest: {latest}', flush=True)

    if current == latest:
        print('Up to date. Silent exit.', flush=True)
        return

    # Check if we already notified about this version
    last_notified = get_last_notified()
    if last_notified == latest:
        print(f'Already notified about {latest}. Silent exit.', flush=True)
        return

    # New version available
    print(f'New version found: {latest}', flush=True)

    changelog = fetch_changelog()
    section = extract_version_section(changelog, latest) if changelog else None

    msg = format_telegram_message(current, latest, section)

    if send_telegram(msg):
        save_notified(latest)
        print(f'Notification sent for {latest}', flush=True)
    else:
        print('Failed to send notification', flush=True)


if __name__ == '__main__':
    main()
