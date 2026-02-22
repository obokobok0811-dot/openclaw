#!/usr/bin/env python3
"""Simple Gmail collector (readonly) - saves messages to JSONL
Requires: credentials/google_oauth_client.json
"""
import os
import json
import argparse
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']


def get_gmail_service(creds_path='credentials/google_oauth_client.json', token_path='credentials/token.json'):
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
        creds = flow.run_local_server(port=0)
        with open(token_path, 'w') as fh:
            fh.write(creds.to_json())
    service = build('gmail', 'v1', credentials=creds)
    return service


def fetch_messages(service, user_id='me', q=None, max_results=100):
    messages = []
    request = service.users().messages().list(userId=user_id, q=q, maxResults=max_results)
    while request is not None:
        resp = request.execute()
        for m in resp.get('messages', []):
            msg = service.users().messages().get(userId=user_id, id=m['id'], format='full').execute()
            messages.append(msg)
        request = service.users().messages().list_next(request, resp)
    return messages


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--since_days', type=int, default=365)
    p.add_argument('--out', type=str, default='poc/data/gmail.jsonl')
    args = p.parse_args()

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    svc = get_gmail_service()
    # query: newer_than:365d
    q = f'newer_than:{args.since_days}d'
    msgs = fetch_messages(svc, q=q, max_results=500)
    with open(args.out, 'w') as fh:
        for m in msgs:
            fh.write(json.dumps(m) + '\n')
    print(f'wrote {len(msgs)} messages to {args.out}')

if __name__=='__main__':
    main()
