#!/usr/bin/env python3
"""
Mini-Searcher: search obsidian_map.csv and show matching files or display file content (including from archives)
Usage:
  obsidian_search.py --query "KRW-BTC BUY" [--date YYYY-MM-DD] [--show]
"""
import argparse, csv, re, subprocess, sys
from pathlib import Path
OPS=Path('/Users/andy/.openclaw/workspace/ops')
MAP=OPS/'obsidian_map.csv'
ROOT=Path('/Users/andy/Documents/Obsidian/Obsidian Vault/OpenClaw/Sessions')
ARCH=OPS/'ob_archive_v2'

def search(query, date=None):
    q=query.lower()
    results=[]
    if not MAP.exists():
        print('no index')
        return results
    with MAP.open() as f:
        r=csv.DictReader(f)
        for row in r:
            if date and row['date']!=date:
                continue
            hay = (row['tickers'] + ' ' + row['signals'] + ' ' + row['errors']).lower()
            if all(tok in hay for tok in q.split()):
                results.append(row)
    return results

parser=argparse.ArgumentParser()
parser.add_argument('--query',required=True)
parser.add_argument('--date')
parser.add_argument('--show',action='store_true')
args=parser.parse_args()
res=search(args.query,args.date)
if not res:
    print('No matches')
    sys.exit(0)
print(f"Found {len(res)} matches:\n")
for i,row in enumerate(res):
    print(i+1, row['date'], row['file'], row['tickers'], row['signals'], row['errors'])

if args.show:
    # show first match
    target=Path(ROOT)/res[0]['file']
    if target.exists():
        print('\n---- FILE: ',target)
        print(target.read_text())
    else:
        # try to extract from archive
        tar=ARCH/f'ob_{res[0]["date"]}.tar.gz'
        if tar.exists():
            import tarfile
            with tarfile.open(tar) as tf:
                member=str(res[0]['file'])
                try:
                    m=tf.getmember(member)
                    f=tf.extractfile(m)
                    print(f.read().decode())
                except Exception as e:
                    print('cannot extract',e)
    
