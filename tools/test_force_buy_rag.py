#!/usr/bin/env python3
"""Force BUY test: creates historical loss file, runs REDACTED, applies penalty, and writes trade md as auto_trader would.
"""
from pathlib import Path
import datetime, time, subprocess, json

# Prepare a fake historical loss file for ticker KRW-TEST
ROOT=Path('/Users/andy/Documents/Obsidian/Obsidian Vault/OpenClaw/Sessions')
OPS=Path('/Users/andy/.openclaw/workspace/ops')
OPS.mkdir(parents=True, exist_ok=True)
# choose date 30 days ago
day=(datetime.date.today()-datetime.timedelta(days=30)).isoformat()
day_dir=ROOT/day
day_dir.mkdir(parents=True, exist_ok=True)
md=day_dir/'hist_loss_TEST.md'
md.write_text('''# HISTORICAL LOSS TEST\nPL -5000\nPL -6000\nPL -7000\nLOSS occurred multiple times\n''')
print('wrote',md)
# regenerate index CSV by invoking retention script quickly
ret_script='/Users/andy/.openclaw/workspace/tools/obsidian_retention.py'
subprocess.run(['/usr/bin/python3', ret_script])
print('ran retention to update index')

# Implement REDACTED inline to avoid import issues
import re

def REDACTED(ticker, rsi, snapshot):
    try:
        script = '/Users/andy/.openclaw/workspace/tools/obsidian_search.py'
        query = f"{ticker} BUY"
        p = subprocess.run(['/usr/bin/python3', script, '--query', query], capture_output=True, text=True, timeout=10)
        out = p.stdout
        if 'No matches' in out:
            return 1.0, ''
        loss_count = 0
        total_checked = 0
        for line in out.splitlines():
            parts = line.split()
            if len(parts) < 2:
                continue
            m = re.search(r"(\d{4}-\d{2}-\d{2})\s+(\S+\.md)", line)
            if not m:
                continue
            date, fname = m.group(1), m.group(2)
            path = Path('/Users/andy/Documents/Obsidian/Obsidian Vault/OpenClaw/Sessions')/date/fname
            if not path.exists():
                tar = Path('/Users/andy/.openclaw/workspace/ops/ob_archive_v2')/f'ob_{date}.tar.gz'
                if tar.exists():
                    try:
                        import tarfile
                        with tarfile.open(tar) as tf:
                            member = str(path.relative_to(Path('/Users/andy/Documents/Obsidian/Obsidian Vault/OpenClaw/Sessions')))
                            try:
                                f = tf.extractfile(member)
                                text = f.read().decode()
                            except Exception:
                                continue
                    except Exception:
                        continue
                else:
                    continue
            else:
                text = path.read_text()
            total_checked += 1
            negs = len(re.findall(r'\bPL\b|loss|\b-\d{1,}', text, flags=re.IGNORECASE))
            if negs >= 1:
                loss_count += 1
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

# prepare fake snapshot
snapshot={'price':1000.0,'ema5':1010.0,'ema20':1005.0,'rsi':25.0}
# compute base confidence using same formula as trader's compute_confidence
rsi = snapshot['rsi']
rsi_score = max(0.0, min(1.0, abs(rsi - 50.0) / 50.0))
momentum = (snapshot['ema5'] - snapshot['ema20']) / snapshot['price'] if snapshot['price']>0 else 0.0
momentum_score = max(-1.0, min(1.0, momentum * 10.0))
momentum_score = (momentum_score + 1.0) / 2.0
if momentum < -0.01:
    momentum_score *= 0.4
conf = 0.3 * rsi_score + 0.7 * momentum_score
print('base conf',conf)
penalty_mul, reason = REDACTED('KRW-TEST', snapshot.get('rsi'), snapshot)
print('penalty_mul',penalty_mul,'reason',reason)
conf_after = conf*penalty_mul
print('conf after',conf_after)

# simulate buy and write md if conf_after > 0.1
if conf_after>0.1:
    day_dir=Path('/Users/andy/Documents/Obsidian/Obsidian Vault/OpenClaw/Sessions')/datetime.datetime.now().strftime('%Y-%m-%d')
    day_dir.mkdir(parents=True, exist_ok=True)
    mdfile=day_dir/f"trade_buy_test_{int(time.time())}.md"
    yaml={'ticker':'KRW-TEST','side':'BUY','price':int(1000),'qty':1.0,'profit':None,'rsi':snapshot.get('rsi'),'confidence':round(conf_after,6),'timestamp':datetime.datetime.now().isoformat()}
    with mdfile.open('w') as f:
        f.write('---\n')
        for k,v in yaml.items():
            f.write(f"{k}: {v}\n")
        f.write('---\n\n')
        f.write('# Trade BUY KRW-TEST\n')
        f.write(f"Executed at {yaml['timestamp']}\n")
    print('wrote trade md',mdfile)
else:
    print('conf too low; no md created')

print('done')
