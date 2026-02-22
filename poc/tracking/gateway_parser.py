#!/usr/bin/env python3
"""
Gateway log parser: extract AI model usage from OpenClaw gateway logs.
Pairs 'embedded run start' with 'embedded run done' to track each call.
Runs hourly to ingest new log entries into usage.jsonl.

Token counts: gateway logs don't include per-call tokens directly.
This parser estimates based on duration + model speed benchmarks,
and enriches with session_status snapshots when available.
"""
import json, re, datetime, os, sys
from pathlib import Path
from collections import defaultdict

ROOT = Path('/Users/andy/.openclaw/workspace')
LOG_DIR = Path('/tmp/openclaw')
TRACKING_DIR = ROOT / 'poc' / 'tracking'
TRACKING_DIR.mkdir(parents=True, exist_ok=True)
USAGE_FILE = TRACKING_DIR / 'usage.jsonl'
STATE_FILE = TRACKING_DIR / 'parser_state.json'

sys.path.insert(0, str(ROOT))
from poc.tracking.tracker import log_call, estimate_cost, PRICING

# Approximate tokens/sec output speed per model (rough benchmarks)
OUTPUT_SPEED = {
    'gpt-5-mini': 120,
    'gpt-5': 80,
    'gpt-4o': 100,
    'gpt-4o-mini': 150,
    'o1': 50,
    'o1-mini': 80,
    'o3': 60,
    'o3-mini': 100,
    'o4-mini': 100,
    'claude-opus-4': 40,
    'claude-opus-4.5': 40,
    'claude-opus-4.6': 40,
    'claude-sonnet-4': 80,
    'claude-haiku-3.5': 150,
    'gemini-2.5-pro': 80,
    'gemini-2.5-flash': 150,
    'gemini-2.0-flash': 200,
    'grok-3': 70,
    'grok-3-mini': 120,
    'grok-2': 80,
}

# Input/output ratio (typical: input is ~3-5x output for chat)
IO_RATIO = 4.0

def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {'last_offset': 0, 'last_file': ''}

def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f)

def parse_run_start(msg):
    """Parse: embedded run start: runId=X sessionId=Y provider=Z model=W thinking=T messageChannel=C"""
    m = re.search(r'runId=(\S+)\s+sessionId=(\S+)\s+provider=(\S+)\s+model=(\S+)\s+thinking=(\S+)\s+messageChannel=(\S+)', msg)
    if m:
        return {
            'runId': m.group(1),
            'sessionId': m.group(2),
            'provider': m.group(3),
            'model': m.group(4),
            'thinking': m.group(5),
            'channel': m.group(6),
        }
    return None

def parse_run_done(msg):
    """Parse: embedded run done: runId=X sessionId=Y durationMs=Z aborted=B"""
    m = re.search(r'runId=(\S+)\s+sessionId=(\S+)\s+durationMs=(\d+)\s+aborted=(\S+)', msg)
    if m:
        return {
            'runId': m.group(1),
            'sessionId': m.group(2),
            'durationMs': int(m.group(3)),
            'aborted': m.group(4) == 'true',
        }
    return None

def estimate_tokens_from_duration(model, duration_ms):
    """Rough estimate: output_tokens ≈ duration_sec * speed, input ≈ output * ratio."""
    # Strip provider prefix (e.g., github-copilot/gpt-5-mini -> gpt-5-mini)
    clean_model = model.split('/')[-1] if '/' in model else model

    speed = OUTPUT_SPEED.get(clean_model, 80)
    duration_sec = duration_ms / 1000.0

    # Subtract ~2s for network/setup overhead
    effective_sec = max(0.5, duration_sec - 2.0)

    output_tokens = int(effective_sec * speed)
    input_tokens = int(output_tokens * IO_RATIO)

    return input_tokens, output_tokens

def ingest_log_file(log_path, start_offset=0):
    """Parse a single gateway log file and return new usage entries."""
    runs = {}  # runId -> start data
    completed = []

    with open(log_path) as f:
        f.seek(start_offset)
        for line in f:
            try:
                d = json.loads(line.strip())
                msg = d.get('1', '')
                if not isinstance(msg, str):
                    continue
                ts = d.get('time', d.get('_meta', {}).get('date', ''))

                if 'embedded run start:' in msg:
                    info = parse_run_start(msg)
                    if info:
                        info['start_time'] = ts
                        runs[info['runId']] = info

                elif 'embedded run done:' in msg:
                    info = parse_run_done(msg)
                    if info and info['runId'] in runs:
                        start = runs.pop(info['runId'])
                        if not info['aborted']:
                            completed.append({
                                'start': start,
                                'done': info,
                                'end_time': ts,
                            })
            except Exception:
                continue

        end_offset = f.tell()

    return completed, end_offset

def process_completed_runs(completed):
    """Convert completed runs to usage log entries."""
    new_entries = []
    for run in completed:
        start = run['start']
        done = run['done']

        full_model = start['model']
        clean_model = full_model.split('/')[-1] if '/' in full_model else full_model
        provider = start['provider']

        input_tokens, output_tokens = estimate_tokens_from_duration(
            full_model, done['durationMs']
        )

        # Map channel to task type
        channel = start.get('channel', 'unknown')
        task_map = {
            'telegram': 'chat',
            'webchat': 'chat',
            'discord': 'chat',
            'whatsapp': 'chat',
            'cron': 'automation',
            'heartbeat': 'system',
        }
        task_type = task_map.get(channel, 'general')

        entry = log_call(
            model=clean_model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            task_type=task_type,
            provider=provider.split('-')[0] if '-' in provider else provider,
            latency_ms=done['durationMs'],
            metadata={
                'runId': start['runId'],
                'sessionId': start['sessionId'],
                'channel': channel,
                'thinking': start.get('thinking', 'off'),
                'full_model': full_model,
                'estimation': 'duration_based',
            }
        )
        new_entries.append(entry)

    return new_entries

def run():
    state = load_state()

    # Find today's log file
    today = datetime.date.today().isoformat()
    log_file = LOG_DIR / f'openclaw-{today}.log'

    if not log_file.exists():
        print(f'No log file for today: {log_file}', flush=True)
        return

    # Determine offset
    offset = 0
    if state.get('last_file') == str(log_file):
        offset = state.get('last_offset', 0)

    completed, end_offset = ingest_log_file(log_file, offset)

    if completed:
        entries = process_completed_runs(completed)
        print(f'Ingested {len(entries)} API calls from gateway log', flush=True)
        for e in entries:
            print(f'  {e["model"]} | {e["total_tokens"]} tokens | ${e["cost_usd"]:.6f} | {e["task_type"]} | {e.get("latency_ms", 0)}ms', flush=True)
    else:
        print(f'No new completed runs since offset {offset}', flush=True)

    # Save state
    save_state({'last_file': str(log_file), 'last_offset': end_offset})

if __name__ == '__main__':
    run()
