#!/usr/bin/env python3
"""
eth_alert.py - simple alert handler stub
Usage:
  eth_alert.py --file /path/to/file
  eth_alert.py --json '{...}'

Behavior:
 - Reads event JSON (file or stdin/arg)
 - Appends a short summary line to /Users/andy/.openclaw/workspace/zzuvi_notify.log
 - Attempts to send the message to the Telegram group configured in ~/.openclaw/openclaw.json (account: main, group: -1003599827914)
 - If Telegram send fails, logs the HTTP response to the same log.

This is a non-destructive stub to restore cron behavior. Provide a real implementation later if desired.
"""
import sys, os, json, argparse, subprocess, shlex
from datetime import datetime

LOG_PATH = '/Users/andy/.openclaw/workspace/zzuvi_notify.log'
CONFIG_PATH = os.path.expanduser('~/.openclaw/openclaw.json')
DEFAULT_GROUP = '-1003599827914'


def load_config():
    try:
        with open(CONFIG_PATH,'r') as f:
            return json.load(f)
    except Exception as e:
        return {}


def extract_bot_token(cfg, account='main'):
    try:
        return cfg['channels']['telegram']['accounts'][account]['botToken']
    except Exception:
        return None


def append_log(text):
    ts = datetime.now().isoformat()
    with open(LOG_PATH,'a') as f:
        f.write(f"{ts} - {text}\n")


def send_telegram_photo(token, chat_id, photo_path, caption=None):
    if not token:
        return (False, 'no-token')
    if not os.path.exists(photo_path):
        return (False, 'no-file')
    url = f"https://api.telegram.org/bot{token}/sendPhoto"
    # Use curl without writing to temp files and capture output
    cmd = [
        'curl','-sS','-w','%{http_code}','-o','/tmp/eth_alert_curl_out',
        '-F', f'chat_id={chat_id}',
        '-F', f'photo=@{photo_path}'
    ]
    if caption:
        cmd += ['-F', f'caption={caption}']
    try:
        proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
        http_code = None
        # curl writes http_code to stdout because of -w
        if proc.stdout:
            try:
                http_code = int(proc.stdout.strip())
            except Exception:
                http_code = None
        # read response body from file
        body = ''
        try:
            body = open('/tmp/eth_alert_curl_out','r').read().strip()
        except Exception:
            body = proc.stderr.strip()
        if http_code and 200 <= http_code < 300:
            return (True, f'sent_http_{http_code}')
        else:
            return (False, f'http_{http_code}_body:{body[:300]}')
    except Exception as e:
        return (False, str(e))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--file', help='path to media file', default=None)
    p.add_argument('--json', help='event JSON string', default=None)
    args = p.parse_args()

    data = None
    if args.file:
        if os.path.exists(args.file):
            # if file is likely JSON, try parse; else create simple snapshot
            if args.file.lower().endswith('.json'):
                try:
                    data = json.load(open(args.file))
                except Exception:
                    data = {'file': args.file}
            else:
                data = {'file': args.file}
        else:
            append_log(f"eth_alert: file not found: {args.file}")
            print('file-not-found', file=sys.stderr)
            sys.exit(2)
    elif args.json:
        try:
            data = json.loads(args.json)
        except Exception:
            data = {'raw': args.json}
    else:
        # try read stdin
        try:
            txt = sys.stdin.read()
            if txt.strip():
                try:
                    data = json.loads(txt)
                except Exception:
                    data = {'stdin': txt[:1000]}
            else:
                append_log('eth_alert: no input')
                sys.exit(0)
        except Exception:
            append_log('eth_alert: no input and no args')
            sys.exit(0)

    # build summary
    summary = None
    if isinstance(data, dict):
        # try common snapshot fields
        if 'event' in data and 'snapshot' in data:
            s = data['snapshot']
            summary = f"{data.get('event')} {s.get('ticker','?')} price={s.get('price','?')}"
        elif 'file' in data:
            summary = f"file: {os.path.basename(data['file'])}"
        else:
            # small stringify
            try:
                summary = json.dumps(data)[:200]
            except Exception:
                summary = str(data)[:200]
    else:
        summary = str(data)[:200]

    append_log(f"eth_alert: {summary}")

    # attempt telegram send using main account
    cfg = load_config()
    token = extract_bot_token(cfg, 'main')
    chat_id = DEFAULT_GROUP

    if args.file and os.path.exists(args.file):
        ok, msg = send_telegram_photo(token, chat_id, args.file, caption=summary)
        append_log(f"eth_alert: telegram send result: {ok} {msg}")
    else:
        # send simple message via sendMessage
        if token:
            text = summary
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            cmd = ['curl','-s','-X','POST', url, '-d', f'chat_id={chat_id}', '-d', f'text={text}']
            try:
                proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
                # curl returns 0 on success; response body in proc.stdout
                body = proc.stdout.strip()
                append_log(f"eth_alert: sendMessage rc={proc.returncode} out={body[:500]}")
            except Exception as e:
                append_log(f"eth_alert: sendMessage error: {e}")

    print('ok')

if __name__=='__main__':
    main()
