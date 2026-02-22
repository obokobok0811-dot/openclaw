#!/usr/bin/env python3
"""Simple Google Calendar collector (readonly) - saves events to JSONL
Requires: credentials/google_oauth_client.json
"""
import os
import json
import argparse
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']


def get_calendar_service(creds_path='credentials/google_oauth_client.json', token_path='credentials/calendar_token.json'):
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
        creds = flow.run_local_server(port=0)
        with open(token_path, 'w') as fh:
            fh.write(creds.to_json())
    service = build('calendar', 'v3', credentials=creds)
    return service


def fetch_events(service, calendar_id='primary', time_min=None, time_max=None):
    events = []
    page_token = None
    while True:
        resp = service.events().list(calendarId=calendar_id, timeMin=time_min, timeMax=time_max, pageToken=page_token).execute()
        events.extend(resp.get('items', []))
        page_token = resp.get('nextPageToken')
        if not page_token:
            break
    return events


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--since_days', type=int, default=365)
    p.add_argument('--out', type=str, default='poc/data/calendar.jsonl')
    args = p.parse_args()

    import datetime
    time_max = datetime.datetime.utcnow().isoformat() + 'Z'
    time_min = (datetime.datetime.utcnow() - datetime.timedelta(days=args.since_days)).isoformat() + 'Z'

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    svc = get_calendar_service()
    evts = fetch_events(svc, time_min=time_min, time_max=time_max)
    with open(args.out, 'w') as fh:
        for e in evts:
            fh.write(json.dumps(e) + '\n')
    print(f'wrote {len(evts)} events to {args.out}')

if __name__=='__main__':
    main()
