from __future__ import print_function
import os
import json
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

TOKEN_FILE = '/Users/andy/.openclaw/workspace/credentials/gmail_token.json'
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
service = build('gmail', 'v1', credentials=creds)
# list messages excluding SPAM and TRASH, label 'INBOX' and not 'SPAM'
query = 'in:inbox -label:spam'
results = service.users().messages().list(userId='me', q=query, maxResults=20).execute()
msgs = results.get('messages', [])
output = []
count = 0
for m in msgs:
    if count>=10: break
    msg = service.users().messages().get(userId='me', id=m['id'], format='metadata', metadataHeaders=['From','Subject','Date']).execute()
    headers = {h['name']:h['value'] for h in msg.get('payload',{}).get('headers',[])}
    snippet = msg.get('snippet','')
    output.append({'id':m['id'], 'from':headers.get('From',''), 'subject':headers.get('Subject',''), 'date':headers.get('Date',''), 'snippet':snippet})
    count+=1
print(json.dumps(output, ensure_ascii=False, indent=2))
