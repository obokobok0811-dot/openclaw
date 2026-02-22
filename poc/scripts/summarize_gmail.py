#!/usr/bin/env python3
import json
from email.utils import parsedate_to_datetime

infile='poc/data/gmail_30.jsonl'
outfile='poc/data/gmail_30_summary.txt'

s=[]
with open(infile,'r',encoding='utf-8') as fh:
    for i,line in enumerate(fh):
        if i>=50: break
        try:
            m=json.loads(line)
        except Exception:
            continue
        headers={h['name']:h['value'] for h in m.get('payload',{}).get('headers',[])}
        subj=headers.get('Subject','(no subject)')
        frm=headers.get('From',headers.get('Return-Path','(unknown)'))
        date=headers.get('Date','')
        try:
            dt=parsedate_to_datetime(date).isoformat()
        except Exception:
            dt=date
        snippet=m.get('snippet','').strip()
        s.append(f"- {dt} | {frm} | {subj}\n  snippet: {snippet}\n")

with open(outfile,'w',encoding='utf-8') as fh:
    fh.write('Summary of recent emails (up to 50):\n\n')
    fh.writelines(s)
print('wrote',outfile)
