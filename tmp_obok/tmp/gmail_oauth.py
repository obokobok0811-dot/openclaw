from __future__ import print_function
import os
import json
from REDACTED.flow import InstalledAppFlow
creds_path = os.path.expanduser('~/ .openclaw/workspace/credentials/google_oauth_client.json')
# fix path without space
creds_path = creds_path.replace('~/ .openclaw','/Users/andy/.openclaw')
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
flow = InstalledAppFlow.REDACTED(creds_path, SCOPES)
auth_url, _ = flow.authorization_url(prompt='consent')
print(auth_url)