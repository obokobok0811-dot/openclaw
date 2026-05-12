#!/usr/bin/env python3
"""
AI Model Usage Tracker
- Logs every API call: provider, model, tokens, cost, task type
- JSONL storage
- Daily/weekly/monthly cost reports with filters
"""
import json, datetime, os, uuid
from pathlib import Path

ROOT = Path('/Users/andy/.openclaw/workspace')
LOG_DIR = ROOT / 'poc' / 'tracking'
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / 'usage.jsonl'

# === Pricing per 1M tokens (USD, as of 2026-02) ===
PRICING = {
    # Anthropic
    'claude-opus-4': {'input': 15.00, 'output': 75.00},
    'claude-opus-4.5': {'input': 15.00, 'output': 75.00},
    'claude-sonnet-4': {'input': 3.00, 'output': 15.00},
    'claude-haiku-3.5': {'input': 0.80, 'output': 4.00},
    # OpenAI
    'gpt-5': {'input': 10.00, 'output': 30.00},
    'gpt-5-mini': {'input': 1.50, 'output': 6.00},
    'gpt-4o': {'input': 2.50, 'output': 10.00},
    'gpt-4o-mini': {'input': 0.15, 'output': 0.60},
    'o1': {'input': 15.00, 'output': 60.00},
    'o1-mini': {'input': 3.00, 'output': 12.00},
    'o3': {'input': 10.00, 'output': 40.00},
    'o3-mini': {'input': 1.10, 'output': 4.40},
    'o4-mini': {'input': 1.10, 'output': 4.40},
    # Google
    'gemini-2.5-pro': {'input': 1.25, 'output': 10.00},
    'gemini-2.5-flash': {'input': 0.15, 'output': 0.60},
    'gemini-2.0-flash': {'input': 0.10, 'output': 0.40},
    # xAI
    'grok-3': {'input': 3.00, 'output': 15.00},
    'grok-3-mini': {'input': 0.30, 'output': 0.50},
    'grok-2': {'input': 2.00, 'output': 10.00},
}

# Provider detection
PROVIDER_MAP = {
    'claude': 'anthropic',
    'gpt': 'openai',
    'o1': 'openai',
    'o3': 'openai',
    'o4': 'openai',
    'gemini': 'google',
    'grok': 'xai',
}

def detect_provider(model: str) -> str:
    model_lower = model.lower()
    for prefix, provider in PROVIDER_MAP.items():
        if model_lower.startswith(prefix):
            return provider
    return 'unknown'

def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate cost in USD."""
    pricing = None
    model_lower = model.lower()
    # Exact match first
    if model_lower in PRICING:
        pricing = PRICING[model_lower]
    else:
        # Fuzzy match: find longest prefix match
        for key in sorted(PRICING.keys(), key=len, reverse=True):
            if model_lower.startswith(key) or key.startswith(model_lower):
                pricing = PRICING[key]
                break
    if not pricing:
        return 0.0
    cost = (input_tokens * pricing['input'] + output_tokens * pricing['output']) / 1_000_000
    return round(cost, 6)

def log_call(
    model: str,
    input_tokens: int,
    output_tokens: int,
    task_type: str = 'general',
    provider: str = None,
    latency_ms: int = None,
    metadata: dict = None,
):
    """Log a single API call."""
    if provider is None:
        provider = detect_provider(model)

    cost = estimate_cost(model, input_tokens, output_tokens)

    entry = {
        'id': str(uuid.uuid4())[:8],
        'timestamp': datetime.datetime.now().isoformat(),
        'provider': provider,
        'model': model,
        'input_tokens': input_tokens,
        'output_tokens': output_tokens,
        'total_tokens': input_tokens + output_tokens,
        'cost_usd': cost,
        'task_type': task_type,
    }
    if latency_ms is not None:
        entry['latency_ms'] = latency_ms
    if metadata:
        entry['metadata'] = metadata

    with open(LOG_FILE, 'a') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')

    return entry

def load_logs(since: datetime.datetime = None, until: datetime.datetime = None,
              model: str = None, provider: str = None, task_type: str = None):
    """Load and filter log entries."""
    if not LOG_FILE.exists():
        return []

    entries = []
    with open(LOG_FILE) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            ts = datetime.datetime.fromisoformat(entry['timestamp'])

            if since and ts < since:
                continue
            if until and ts > until:
                continue
            if model and entry.get('model', '').lower() != model.lower():
                continue
            if provider and entry.get('provider', '').lower() != provider.lower():
                continue
            if task_type and entry.get('task_type', '').lower() != task_type.lower():
                continue

            entries.append(entry)
    return entries

def generate_report(period: str = 'daily', model: str = None,
                    provider: str = None, task_type: str = None):
    """Generate cost report. period: daily, weekly, monthly, all."""
    now = datetime.datetime.now()

    if period == 'daily':
        since = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == 'weekly':
        since = now - datetime.timedelta(days=now.weekday())
        since = since.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == 'monthly':
        since = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        since = None

    entries = load_logs(since=since, model=model, provider=provider, task_type=task_type)

    if not entries:
        return {
            'period': period,
            'since': since.isoformat() if since else 'all',
            'until': now.isoformat(),
            'total_calls': 0,
            'total_cost_usd': 0.0,
            'total_input_tokens': 0,
            'total_output_tokens': 0,
            'by_provider': {},
            'by_model': {},
            'by_task': {},
        }

    total_cost = sum(e.get('cost_usd', 0) for e in entries)
    total_input = sum(e.get('input_tokens', 0) for e in entries)
    total_output = sum(e.get('output_tokens', 0) for e in entries)

    # Group by provider
    by_provider = {}
    for e in entries:
        p = e.get('provider', 'unknown')
        if p not in by_provider:
            by_provider[p] = {'calls': 0, 'cost_usd': 0.0, 'tokens': 0}
        by_provider[p]['calls'] += 1
        by_provider[p]['cost_usd'] += e.get('cost_usd', 0)
        by_provider[p]['tokens'] += e.get('total_tokens', 0)

    # Group by model
    by_model = {}
    for e in entries:
        m = e.get('model', 'unknown')
        if m not in by_model:
            by_model[m] = {'calls': 0, 'cost_usd': 0.0, 'input_tokens': 0, 'output_tokens': 0}
        by_model[m]['calls'] += 1
        by_model[m]['cost_usd'] += e.get('cost_usd', 0)
        by_model[m]['input_tokens'] += e.get('input_tokens', 0)
        by_model[m]['output_tokens'] += e.get('output_tokens', 0)

    # Group by task type
    by_task = {}
    for e in entries:
        t = e.get('task_type', 'general')
        if t not in by_task:
            by_task[t] = {'calls': 0, 'cost_usd': 0.0, 'tokens': 0}
        by_task[t]['calls'] += 1
        by_task[t]['cost_usd'] += e.get('cost_usd', 0)
        by_task[t]['tokens'] += e.get('total_tokens', 0)

    # Round costs
    for d in [by_provider, by_model, by_task]:
        for v in d.values():
            v['cost_usd'] = round(v['cost_usd'], 4)

    return {
        'period': period,
        'since': since.isoformat() if since else 'all',
        'until': now.isoformat(),
        'total_calls': len(entries),
        'total_cost_usd': round(total_cost, 4),
        'total_input_tokens': total_input,
        'total_output_tokens': total_output,
        'by_provider': by_provider,
        'by_model': by_model,
        'by_task': by_task,
    }

def format_report(report: dict) -> str:
    """Format report as human-readable text."""
    lines = [
        f"📊 AI 사용량 리포트 ({report['period']})",
        f"기간: {report['since'][:19]} ~ {report['until'][:19]}",
        "",
        f"총 호출: {report['total_calls']}회",
        f"총 비용: ${report['total_cost_usd']:.4f}",
        f"총 토큰: {report['total_input_tokens']:,} in / {report['total_output_tokens']:,} out",
        "",
    ]

    if report['by_provider']:
        lines.append("Provider별:")
        for p, v in sorted(report['by_provider'].items(), key=lambda x: -x[1]['cost_usd']):
            lines.append(f"  {p}: {v['calls']}회, ${v['cost_usd']:.4f}, {v['tokens']:,} tokens")
        lines.append("")

    if report['by_model']:
        lines.append("Model별:")
        for m, v in sorted(report['by_model'].items(), key=lambda x: -x[1]['cost_usd']):
            lines.append(f"  {m}: {v['calls']}회, ${v['cost_usd']:.4f}")
        lines.append("")

    if report['by_task']:
        lines.append("Task별:")
        for t, v in sorted(report['by_task'].items(), key=lambda x: -x[1]['cost_usd']):
            lines.append(f"  {t}: {v['calls']}회, ${v['cost_usd']:.4f}")

    return '\n'.join(lines)

if __name__ == '__main__':
    import sys
    args = sys.argv[1:]

    if not args or args[0] == 'help':
        print("Usage:")
        print("  python3 tracker.py log <model> <input_tokens> <output_tokens> [task_type]")
        print("  python3 tracker.py report [daily|weekly|monthly|all] [--model X] [--provider X] [--task X]")
        print("  python3 tracker.py pricing                  # show pricing table")
        print("  python3 tracker.py stats                    # quick summary")
        sys.exit(0)

    if args[0] == 'log':
        model = args[1]
        input_t = int(args[2])
        output_t = int(args[3])
        task = args[4] if len(args) > 4 else 'general'
        entry = log_call(model, input_t, output_t, task_type=task)
        print(f"Logged: {entry['model']} | {entry['total_tokens']} tokens | ${entry['cost_usd']:.6f} | {entry['task_type']}")

    elif args[0] == 'report':
        period = args[1] if len(args) > 1 else 'daily'
        # Parse optional filters
        model_f = provider_f = task_f = None
        for i, a in enumerate(args):
            if a == '--model' and i + 1 < len(args): model_f = args[i + 1]
            if a == '--provider' and i + 1 < len(args): provider_f = args[i + 1]
            if a == '--task' and i + 1 < len(args): task_f = args[i + 1]
        report = generate_report(period, model=model_f, provider=provider_f, task_type=task_f)
        print(format_report(report))

    elif args[0] == 'pricing':
        print("Model Pricing (per 1M tokens, USD):")
        print(f"{'Model':<25} {'Input':>8} {'Output':>8}")
        print("-" * 45)
        for m, p in sorted(PRICING.items()):
            print(f"{m:<25} ${p['input']:>7.2f} ${p['output']:>7.2f}")

    elif args[0] == 'stats':
        report = generate_report('all')
        print(format_report(report))
