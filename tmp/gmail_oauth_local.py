from __future__ import print_function
import os, json, stat
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

CREDS_FILE = '/Users/andy/.openclaw/workspace/credentials/google_oauth_client.json'
TOKEN_FILE = '/Users/andy/.openclaw/workspace/credentials/gmail_token.json'
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']


def save_token(creds, path):
    with open(path, 'w') as f:
        f.write(creds.to_json())
    os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)


def main():
    flow = InstalledAppFlow.from_client_secrets_file(CREDS_FILE, SCOPES)
    creds = flow.run_local_server(port=0)
    save_token(creds, TOKEN_FILE)
    print('토큰 저장됨:', TOKEN_FILE)

if __name__ == '__main__':
    main()
