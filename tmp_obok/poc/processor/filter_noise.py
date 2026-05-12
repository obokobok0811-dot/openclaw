#!/usr/bin/env python3
"""Filter noise contacts (marketing/newsletter/auto) and output excluded ids list.
Rules:
 - email local part contains 'no-reply' or 'noreply' or 'unsubscribe' or 'mailer'
 - domain in common marketing domains (example list)
 - name contains 'no-reply' or 'noreply'
 - emails that never had a reply are harder to detect; this is a basic heuristic
"""
import sqlite3
import re
import json

MARKETING_DOMAINS = set([
    'news.yahoo.com','newsletter.example.com','mailchimp.com','campaign-archive.com'
])
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+)\.[A-Za-z]{2,}")

def is_noise(name,email):
    if not email:
        return True
    local = email.split('@')[0].lower()
    domain = email.split('@')[-1].lower()
    if any(x in local for x in ('no-reply','noreply','unsubscribe','mailer','bounce','postmaster')):
        return True
    if 'no-reply' in (name or '').lower() or 'noreply' in (name or '').lower():
        return True
    if domain in MARKETING_DOMAINS:
        return True
    # heuristic: numeric-only local parts maybe auto
    if local.isdigit():
        return True
    return False


def main(db='poc/crm.db', out='poc/vectors/excluded_ids.json'):
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    cur.execute('SELECT id,name,canonical_email FROM contacts')
    rows = cur.fetchall()
    excluded = []
    for r in rows:
        cid, name, email = r
        if is_noise(name,email):
            excluded.append(cid)
    # write excluded ids
    with open(out,'w') as fh:
        json.dump(excluded, fh)
    print(f'Excluded {len(excluded)} contacts; written to {out}')

if __name__=='__main__':
    main()
