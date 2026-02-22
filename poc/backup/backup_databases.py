#!/usr/bin/env python3
"""
Automated SQLite Backup System
- Auto-discovers all .db and .sqlite files in workspace
- Creates encrypted tar archive (AES-256-CBC via openssl)
- Uploads to Google Drive (via googleapis)
- Retains last 7 backups (local + remote)
- Telegram alert on failure
"""
import os, json, subprocess, datetime, glob, shutil, sys, urllib.request
from pathlib import Path

# === Config ===
ROOT = Path('/Users/andy/.openclaw/workspace')
BACKUP_DIR = ROOT / 'backups' / 'db'
BACKUP_DIR.mkdir(parents=True, exist_ok=True)
MAX_BACKUPS = 7
PASSPHRASE_FILE = ROOT / 'credentials' / 'backup_passphrase.key'
CRED_PATH = ROOT / 'credentials' / 'telegram_bot.json'
GDRIVE_TOKEN_PATH = ROOT / 'credentials' / 'gdrive_token.json'
GDRIVE_FOLDER_NAME = 'clawd-backups'

# Directories to skip during discovery
SKIP_DIRS = {'.git', 'node_modules', '.venv', 'venv', '__pycache__', 'backups'}

# === Telegram ===
try:
    with open(CRED_PATH) as f:
        cred = json.load(f)
        BOT_TOKEN = cred.get('bot_token', cred.get('token', ''))
except Exception:
    BOT_TOKEN = ''
CHAT_ID = '5510621427'

def send_telegram(text):
    if not BOT_TOKEN:
        print('WARN: no bot token', flush=True)
        return
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    data = json.dumps({'chat_id': CHAT_ID, 'text': text, 'parse_mode': 'HTML'}).encode()
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f'WARN: Telegram send failed: {e}', flush=True)

def alert_failure(stage, error_msg):
    msg = (
        f"🚨 <b>백업 실패 알림</b>\n\n"
        f"단계: {stage}\n"
        f"시각: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"오류: {error_msg[:500]}"
    )
    print(msg, flush=True)
    send_telegram(msg)

# === Step 1: Auto-discover databases ===
def discover_databases():
    dbs = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fname in filenames:
            if fname.endswith('.db') or fname.endswith('.sqlite'):
                fp = Path(dirpath) / fname
                # Verify it's a real SQLite file
                try:
                    with open(fp, 'rb') as f:
                        header = f.read(16)
                    if header[:6] == b'SQLite':
                        dbs.append(fp)
                except Exception:
                    pass
    return dbs

# === Step 2: Safe copy (sqlite3 .backup) ===
def safe_copy_db(db_path, dest_dir):
    """Use sqlite3 .backup for consistent copy, fallback to file copy."""
    dest = dest_dir / db_path.relative_to(ROOT)
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        # Use sqlite3 backup API for consistency
        r = subprocess.run(
            ['sqlite3', str(db_path), f'.backup {str(dest)}'],
            capture_output=True, text=True, timeout=30
        )
        if r.returncode != 0:
            raise Exception(r.stderr)
    except Exception:
        # Fallback: direct copy
        shutil.copy2(db_path, dest)
    return dest

# === Step 3: Create encrypted archive ===
def get_passphrase():
    if PASSPHRASE_FILE.exists():
        return PASSPHRASE_FILE.read_text().strip()
    # Generate new passphrase
    import secrets
    passphrase = secrets.token_urlsafe(32)
    PASSPHRASE_FILE.parent.mkdir(parents=True, exist_ok=True)
    PASSPHRASE_FILE.write_text(passphrase)
    os.chmod(PASSPHRASE_FILE, 0o600)
    print(f'Generated new backup passphrase: {PASSPHRASE_FILE}', flush=True)
    return passphrase

def create_encrypted_archive(staging_dir, timestamp):
    tar_name = f'db_backup_{timestamp}.tar.gz'
    enc_name = f'{tar_name}.enc'
    tar_path = BACKUP_DIR / tar_name
    enc_path = BACKUP_DIR / enc_name

    # Create tar.gz
    r = subprocess.run(
        ['tar', 'czf', str(tar_path), '-C', str(staging_dir), '.'],
        capture_output=True, text=True, timeout=60
    )
    if r.returncode != 0:
        raise Exception(f'tar failed: {r.stderr}')

    # Encrypt with openssl
    passphrase = get_passphrase()
    r = subprocess.run(
        ['openssl', 'enc', '-aes-256-cbc', '-salt', '-pbkdf2',
         '-in', str(tar_path), '-out', str(enc_path),
         '-pass', f'pass:{passphrase}'],
        capture_output=True, text=True, timeout=60
    )
    if r.returncode != 0:
        raise Exception(f'openssl encrypt failed: {r.stderr}')

    # Remove unencrypted tar
    tar_path.unlink()

    return enc_path

# === Step 4: Google Drive upload ===
def upload_to_gdrive(file_path):
    """Upload to Google Drive using REST API with OAuth token."""
    if not GDRIVE_TOKEN_PATH.exists():
        print('WARN: No Google Drive token, skipping upload', flush=True)
        return None

    try:
        with open(GDRIVE_TOKEN_PATH) as f:
            token_data = json.load(f)
        access_token = token_data.get('access_token', '')
        if not access_token:
            print('WARN: Empty access_token, skipping upload', flush=True)
            return None
    except Exception as e:
        print(f'WARN: Could not read gdrive token: {e}', flush=True)
        return None

    # Find or create folder
    folder_id = find_or_create_folder(access_token)

    # Upload file
    file_name = file_path.name
    file_size = file_path.stat().st_size

    metadata = json.dumps({
        'name': file_name,
        'parents': [folder_id] if folder_id else []
    }).encode()

    # Simple upload for files < 5MB, resumable for larger
    if file_size < 5_000_000:
        return simple_upload(access_token, file_path, metadata)
    else:
        return resumable_upload(access_token, file_path, metadata)

def find_or_create_folder(access_token):
    """Find or create the backup folder on Google Drive."""
    # Search for folder
    query = f"name='{GDRIVE_FOLDER_NAME}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    url = f"https://www.googleapis.com/drive/v3/files?q={urllib.request.quote(query)}"
    req = urllib.request.Request(url, headers={'Authorization': f'Bearer {access_token}'})
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read())
        if data.get('files'):
            return data['files'][0]['id']
    except Exception:
        pass

    # Create folder
    meta = json.dumps({
        'name': GDRIVE_FOLDER_NAME,
        'mimeType': 'application/vnd.google-apps.folder'
    }).encode()
    req = urllib.request.Request(
        'https://www.googleapis.com/drive/v3/files',
        data=meta,
        headers={
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
    )
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read())
        return data.get('id')
    except Exception:
        return None

def simple_upload(access_token, file_path, metadata):
    """Multipart upload for small files."""
    import email.generator
    boundary = '----BackupBoundary'
    file_content = file_path.read_bytes()

    body = (
        f'--{boundary}\r\n'
        f'Content-Type: application/json; charset=UTF-8\r\n\r\n'
        f'{metadata.decode()}\r\n'
        f'--{boundary}\r\n'
        f'Content-Type: application/octet-stream\r\n\r\n'
    ).encode() + file_content + f'\r\n--{boundary}--\r\n'.encode()

    req = urllib.request.Request(
        'https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart',
        data=body,
        headers={
            'Authorization': f'Bearer {access_token}',
            'Content-Type': f'multipart/related; boundary={boundary}'
        }
    )
    try:
        resp = urllib.request.urlopen(req, timeout=60)
        data = json.loads(resp.read())
        return data.get('id')
    except Exception as e:
        print(f'WARN: Drive upload failed: {e}', flush=True)
        return None

def resumable_upload(access_token, file_path, metadata):
    """Placeholder for resumable upload (large files)."""
    print('WARN: Large file resumable upload not yet implemented, using simple', flush=True)
    return simple_upload(access_token, file_path, metadata)

# === Step 5: Cleanup old backups ===
def cleanup_local():
    """Keep only MAX_BACKUPS most recent local backups."""
    backups = sorted(BACKUP_DIR.glob('db_backup_*.tar.gz.enc'))
    while len(backups) > MAX_BACKUPS:
        old = backups.pop(0)
        old.unlink()
        print(f'Deleted old backup: {old.name}', flush=True)

def cleanup_gdrive():
    """Keep only MAX_BACKUPS on Google Drive."""
    if not GDRIVE_TOKEN_PATH.exists():
        return
    try:
        with open(GDRIVE_TOKEN_PATH) as f:
            access_token = json.load(f).get('access_token', '')
        if not access_token:
            return

        folder_id = find_or_create_folder(access_token)
        if not folder_id:
            return

        query = f"'{folder_id}' in parents and trashed=false"
        url = f"https://www.googleapis.com/drive/v3/files?q={urllib.request.quote(query)}&orderBy=createdTime"
        req = urllib.request.Request(url, headers={'Authorization': f'Bearer {access_token}'})
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read())
        files = data.get('files', [])

        while len(files) > MAX_BACKUPS:
            old = files.pop(0)
            del_url = f"https://www.googleapis.com/drive/v3/files/{old['id']}"
            del_req = urllib.request.Request(del_url, method='DELETE',
                                            headers={'Authorization': f'Bearer {access_token}'})
            urllib.request.urlopen(del_req, timeout=10)
            print(f'Deleted old Drive backup: {old["name"]}', flush=True)
    except Exception as e:
        print(f'WARN: Drive cleanup failed: {e}', flush=True)

# === Main ===
def run_backup():
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    staging_dir = BACKUP_DIR / f'staging_{timestamp}'
    staging_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Discover
        dbs = discover_databases()
        if not dbs:
            print('No databases found to backup.', flush=True)
            shutil.rmtree(staging_dir, ignore_errors=True)
            return

        print(f'Found {len(dbs)} database(s):', flush=True)
        for db in dbs:
            print(f'  {db.relative_to(ROOT)}', flush=True)

        # Safe copy
        for db in dbs:
            safe_copy_db(db, staging_dir)
        print('Safe copies created.', flush=True)

        # Create encrypted archive
        enc_path = create_encrypted_archive(staging_dir, timestamp)
        enc_size = enc_path.stat().st_size
        print(f'Encrypted archive: {enc_path.name} ({enc_size / 1024:.1f} KB)', flush=True)

        # Upload to Google Drive
        gdrive_id = upload_to_gdrive(enc_path)
        if gdrive_id:
            print(f'Uploaded to Google Drive (id: {gdrive_id})', flush=True)
        else:
            print('Google Drive upload skipped (no token or failed)', flush=True)

        # Cleanup
        cleanup_local()
        cleanup_gdrive()

        # Success notification
        msg = (
            f"✅ <b>DB 백업 완료</b>\n\n"
            f"시각: {timestamp}\n"
            f"데이터베이스: {len(dbs)}개\n"
            f"아카이브: {enc_path.name} ({enc_size / 1024:.1f} KB)\n"
            f"Google Drive: {'✅' if gdrive_id else '⏭️ 건너뜀'}\n"
            f"보존: 최근 {MAX_BACKUPS}개"
        )
        print(msg, flush=True)
        # Only send Telegram on failure; success is silent to avoid noise
        # Uncomment below if you want success notifications:
        # send_telegram(msg)

    except Exception as e:
        alert_failure('backup', str(e))
        raise
    finally:
        shutil.rmtree(staging_dir, ignore_errors=True)

if __name__ == '__main__':
    run_backup()
