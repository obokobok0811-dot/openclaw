#!/usr/bin/env python3
"""Simple Box connector: search files by query and link to contacts by email/name
Requires: credentials/box_token.json with developer_token
"""
import json
import os
from boxsdk import Client, OAuth2
import sqlite3


def get_box_client(token_path='credentials/box_token.json'):
    with open(token_path,'r') as fh:
        cfg = json.load(fh)
    token = cfg.get('developer_token')
    auth = OAuth2(client_id=None, client_secret=None, access_token=token)
    client = Client(auth)
    return client


def search_and_link(query, db='poc/crm.db'):
    client = get_box_client()
    items = client.search().query(query, limit=20)
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    for it in items:
        title = it.name
        url = f"https://app.box.com/file/{it.id}"
        # naive: try to find contact with email or name in title
        cur.execute("SELECT id FROM contacts WHERE canonical_email LIKE ? OR name LIKE ?", (f"%{query}%","%{query}%"))
        row = cur.fetchone()
        if row:
            cid = row[0]
            cur.execute('INSERT INTO documents(contact_id, box_file_id, box_path, title, url) VALUES(?,?,?,?,?)',(cid,str(it.id),'',title,url))
    conn.commit()

if __name__=='__main__':
    import sys
    q = sys.argv[1]
    search_and_link(q)
