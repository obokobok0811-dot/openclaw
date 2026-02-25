from __future__ import print_function
import os, json
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

TOKEN_FILE = '/Users/andy/.openclaw/workspace/credentials/gmail_token.json'
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
service = build('gmail', 'v1', credentials=creds)
q = '신한카드 OR subject:명세서 OR from:shinhancard'
res = service.users().messages().list(userId='me', q=q, maxResults=50).execute()
msgs = res.get('messages', [])
out=[]
for m in msgs:
    msg = service.users().messages().get(userId='me', id=m['id'], format='metadata', metadataHeaders=['From','Subject','Date']).execute()
    headers = {h['name']:h['value'] for h in msg.get('payload',{}).get('headers',[])}
    has_attach=False
    parts = msg.get('payload',{}).get('parts',[])
    for p in parts:
        if p.get('filename'):
            has_attach=True
    out.append({'id':m['id'],'from':headers.get('From',''),'subject':headers.get('Subject',''),'date':headers.get('Date',''),'has_attachment':has_attach})
print(json.dumps(out,ensure_ascii=False,indent=2))
