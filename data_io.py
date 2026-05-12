#!/usr/bin/env python3
import csv
from pathlib import Path
from datetime import datetime

def append_price_csv(symbol, rows, base_dir=None):
    """Append rows to CSV for symbol. rows: iterable of dicts with at least 'date' and 'close'."""
    base = Path(base_dir) if base_dir else Path(__file__).parent / 'data'
    base.mkdir(parents=True, exist_ok=True)
    fn = base / f"{symbol}.csv"
    header = ['date','close','open','high','low','volume']
    write_header = not fn.exists()
    with fn.open('a', newline='') as f:
        w = csv.DictWriter(f, fieldnames=header)
        if write_header:
            w.writeheader()
        for r in rows:
            out = {k: r.get(k,'') for k in header}
            if not out.get('date'):
                out['date'] = datetime.utcnow().isoformat()
            w.writerow(out)

def append_index_csv(name, rows, base_dir=None):
    base = Path(base_dir) if base_dir else Path(__file__).parent / 'data'
    base.mkdir(parents=True, exist_ok=True)
    fn = base / f"{name}.csv"
    header = ['date','value']
    write_header = not fn.exists()
    with fn.open('a', newline='') as f:
        w = csv.DictWriter(f, fieldnames=header)
        if write_header:
            w.writeheader()
        for r in rows:
            out = {'date': r.get('date') , 'value': r.get('value')}
            w.writerow(out)
