#!/usr/bin/env python3
"""Simple contact extractor: reads gmail JSONL and calendar JSONL, extracts names/emails and stores to SQLite"""
import argparse
import json
import sqlite3
import os
import re

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def ensure_db(db_path):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    with open('poc/db/schema.sql','r') as fh:
        conn.executescript(fh.read())
    conn.commit()
    return conn


def parse_email_headers(msg):
    headers = {}
    for h in msg.get('payload',{}).get('headers',[]):
        headers[h['name'].lower()] = h['value']
    return headers


def extract_from_gmail(gmail_path, conn):
    cur = conn.cursor()
    with open(gmail_path,'r') as fh:
        for line in fh:
            m = json.loads(line)
            headers = parse_email_headers(m)
            frm = headers.get('from','')
            # extract email
            emails = EMAIL_RE.findall(frm)
            name = frm
            if emails:
                email = emails[0].lower()
            else:
                email = None
            # insert contact
            if email:
                cur.execute('SELECT id FROM contacts WHERE canonical_email=?',(email,))
                if not cur.fetchone():
                    cur.execute('INSERT INTO contacts(name, canonical_email) VALUES(?,?)',(name,email))
    conn.commit()


def extract_from_calendar(cal_path, conn):
    cur = conn.cursor()
    with open(cal_path,'r') as fh:
        for line in fh:
            e = json.loads(line)
            for a in e.get('attendees',[]) or []:
                email = a.get('email')
                name = a.get('displayName') or email
                if email:
                    cur.execute('SELECT id FROM contacts WHERE canonical_email=?',(email,))
                    if not cur.fetchone():
                        cur.execute('INSERT INTO contacts(name, canonical_email) VALUES(?,?)',(name,email))
    conn.commit()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--gmail')
    p.add_argument('--calendar')
    p.add_argument('--db', default='poc/crm.db')
    args = p.parse_args()

    conn = ensure_db(args.db)
    if args.gmail:
        extract_from_gmail(args.gmail, conn)
    if args.calendar:
        extract_from_calendar(args.calendar, conn)
    print('done')

if __name__=='__main__':
    main()
