#!/usr/bin/env python3
"""
Google Drive OAuth token 생성 스크립트.
credentials/gdrive_credentials.json → credentials/gdrive_token.json
"""
import json
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow

ROOT = Path(__file__).resolve().parent.parent
CREDS = ROOT / 'credentials' / 'gdrive_credentials.json'
TOKEN = ROOT / 'credentials' / 'gdrive_token.json'

SCOPES = ['https://www.googleapis.com/auth/drive.file']

def main():
    flow = InstalledAppFlow.from_client_secrets_file(str(CREDS), SCOPES)
    creds = flow.run_local_server(port=8099, open_browser=True)
    
    token_data = {
        'token': creds.token,
        'refresh_token': creds.refresh_token,
        'token_uri': creds.token_uri,
        'client_id': creds.client_id,
        'client_secret': creds.client_secret,
        'scopes': list(creds.scopes),
    }
    
    TOKEN.write_text(json.dumps(token_data, indent=2))
    TOKEN.chmod(0o600)
    print(f'✅ Token saved to {TOKEN}')

if __name__ == '__main__':
    main()
