#!/usr/bin/env python3
"""
Hourly git auto-sync.
- Stages all changes, commits with timestamp tag
- Pulls with rebase, detects merge conflicts
- Pushes to remote
- On conflict: notifies via Telegram, does NOT force resolve
"""
import subprocess, json, datetime, sys, urllib.request
from pathlib import Path

ROOT = Path('/Users/andy/.openclaw/workspace')
CRED_PATH = ROOT / 'credentials' / 'telegram_bot.json'

try:
    with open(CRED_PATH) as f:
        cred = json.load(f)
        BOT_TOKEN = cred.get('bot_token', cred.get('token', ''))
except Exception:
    BOT_TOKEN = ''
CHAT_ID = '5510621427'

def send_telegram(text):
    if not BOT_TOKEN:
        print('WARN: no bot token', flush=True)
        return
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    data = json.dumps({'chat_id': CHAT_ID, 'text': text, 'parse_mode': 'HTML'}).encode()
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f'WARN: Telegram send failed: {e}', flush=True)

def run(cmd, check=False):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60, cwd=str(ROOT))
    if check and r.returncode != 0:
        raise Exception(f'{cmd} failed: {r.stderr}')
    return r

def sync():
    now = datetime.datetime.now()
    ts = now.strftime('%Y-%m-%d_%H%M%S')
    tag_name = f'sync-{ts}'

    print(f'[{ts}] Starting git sync...', flush=True)

    # Check if we have a remote
    remote = run('git remote').stdout.strip()
    has_remote = bool(remote)

    # Check for changes
    status = run('git status --porcelain').stdout.strip()
    if not status:
        print('No changes to commit.', flush=True)
        return

    # Count changes
    lines = status.split('\n')
    added = sum(1 for l in lines if l.startswith('?') or l.startswith('A'))
    modified = sum(1 for l in lines if l.startswith('M') or l.startswith(' M'))
    deleted = sum(1 for l in lines if l.startswith('D') or l.startswith(' D'))

    # Stage all
    run('git add -A', check=True)

    # Commit with timestamp
    commit_msg = f'auto-sync: {now.strftime("%Y-%m-%d %H:%M:%S KST")} [{added}A/{modified}M/{deleted}D]'
    r = run(f'git commit -m "{commit_msg}"')
    if r.returncode != 0:
        if 'nothing to commit' in r.stdout:
            print('Nothing to commit after staging.', flush=True)
            return
        raise Exception(f'Commit failed: {r.stderr}')

    print(f'Committed: {commit_msg}', flush=True)

    # Tag
    run(f'git tag {tag_name}')
    print(f'Tagged: {tag_name}', flush=True)

    if not has_remote:
        print('No remote configured. Commit and tag created locally.', flush=True)
        print('Set up a remote with: git remote add origin <url>', flush=True)
        return

    # Pull with rebase (detect conflicts)
    r = run(f'git pull --rebase {remote} main')
    if r.returncode != 0:
        stderr = r.stderr + r.stdout
        if 'CONFLICT' in stderr or 'conflict' in stderr.lower():
            # Abort rebase, notify user
            run('git rebase --abort')
            conflict_msg = (
                f"⚠️ <b>Git Merge Conflict 발생</b>\n\n"
                f"시각: {now.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"커밋: {commit_msg}\n\n"
                f"자동 해결하지 않았습니다. 수동 확인이 필요합니다.\n\n"
                f"오류:\n<code>{stderr[:500]}</code>\n\n"
                f"해결 방법:\n"
                f"1. cd {ROOT}\n"
                f"2. git pull --rebase origin main\n"
                f"3. 충돌 파일 수정\n"
                f"4. git add . && git rebase --continue"
            )
            print(conflict_msg, flush=True)
            send_telegram(conflict_msg)
            return
        else:
            # Other pull error
            error_msg = (
                f"🚨 <b>Git Pull 실패</b>\n\n"
                f"시각: {now.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"오류:\n<code>{stderr[:500]}</code>"
            )
            print(error_msg, flush=True)
            send_telegram(error_msg)
            return

    # Push
    r = run(f'git push {remote} main --tags')
    if r.returncode != 0:
        error_msg = (
            f"🚨 <b>Git Push 실패</b>\n\n"
            f"시각: {now.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"오류:\n<code>{r.stderr[:500]}</code>"
        )
        print(error_msg, flush=True)
        send_telegram(error_msg)
        return

    print(f'Pushed to {remote}/main with tag {tag_name}', flush=True)

if __name__ == '__main__':
    try:
        sync()
    except Exception as e:
        error_msg = (
            f"🚨 <b>Git Sync 실패</b>\n\n"
            f"오류: {str(e)[:500]}"
        )
        print(error_msg, flush=True)
        send_telegram(error_msg)
        sys.exit(1)
