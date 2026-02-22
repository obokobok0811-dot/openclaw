#!/usr/bin/env python3
import json, re,datetime
from email.utils import parsedate_to_datetime
IN='poc/data/gmail_30.jsonl'
OUT='poc/data/urgent_alerts.jsonl'
KEYWORDS=['verification','verify','security','alert','password','failed login','unauthorized','billing','verification code','보안','인증코드','복구','변경','경고','알림','로그인 시도']
noise_domains=set(["brave.com","mg.remotemouse.net","email.github.com"])

def domain_of(addr):
    if '@' in addr:
        return addr.split('@')[-1].lower()
    return ''

alerts=[]
with open(IN,'r',encoding='utf-8') as fh:
    for line in fh:
        try:
            m=json.loads(line)
        except Exception:
            continue
        headers={h['name']:h['value'] for h in m.get('payload',{}).get('headers',[])}
        frm=headers.get('From','')
        subj=headers.get('Subject','')
        snippet=m.get('snippet','')
        dom=domain_of(frm)
        if any(d in dom for d in noise_domains):
            continue
        txt=(subj+' '+snippet).lower()
        score=0
        for k in KEYWORDS:
            if k in txt:
                score+=1
        if score>0:
            date=headers.get('Date','')
            try:
                dt=parsedate_to_datetime(date).isoformat()
            except Exception:
                dt=date
            alert={
                'id': m.get('id'),
                'date':dt,
                'from':frm,
                'subject':subj,
                'snippet':snippet,
                'score':score
            }
            alerts.append(alert)

with open(OUT,'w',encoding='utf-8') as fo:
    for a in alerts:
        fo.write(json.dumps(a,ensure_ascii=False)+'\n')
print('wrote',OUT,'alerts:',len(alerts))
