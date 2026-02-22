#!/usr/bin/env python3
"""
Restore SQLite databases from an encrypted backup archive.

Usage:
  python3 restore_databases.py                     # List available backups
  python3 restore_databases.py latest               # Restore from latest
  python3 restore_databases.py db_backup_20260222_143000.tar.gz.enc  # Restore specific
  python3 restore_databases.py <file> --list        # List contents without restoring
  python3 restore_databases.py <file> --dry-run     # Show what would be restored
"""
import os, sys, json, subprocess, shutil, tempfile
from pathlib import Path

ROOT = Path('/Users/andy/.openclaw/workspace')
BACKUP_DIR = ROOT / 'backups' / 'db'
PASSPHRASE_FILE = ROOT / 'credentials' / 'backup_passphrase.key'
RESTORE_DIR = ROOT / 'backups' / 'restored'

def get_passphrase():
    if not PASSPHRASE_FILE.exists():
        print(f'ERROR: Passphrase file not found: {PASSPHRASE_FILE}')
        print('Cannot decrypt backup without the original passphrase.')
        sys.exit(1)
    return PASSPHRASE_FILE.read_text().strip()

def list_backups():
    backups = sorted(BACKUP_DIR.glob('db_backup_*.tar.gz.enc'))
    if not backups:
        print('No backups found.')
        return []
    print(f'Available backups ({len(backups)}):')
    print()
    for i, b in enumerate(backups, 1):
        size = b.stat().st_size / 1024
        ts = b.name.replace('db_backup_', '').replace('.tar.gz.enc', '')
        print(f'  {i}. {b.name}  ({size:.1f} KB)  [{ts}]')
    print()
    print(f'Latest: {backups[-1].name}')
    return backups

def decrypt_archive(enc_path, dest_dir):
    passphrase = get_passphrase()
    tar_path = dest_dir / 'backup.tar.gz'

    r = subprocess.run(
        ['openssl', 'enc', '-aes-256-cbc', '-d', '-salt', '-pbkdf2',
         '-in', str(enc_path), '-out', str(tar_path),
         '-pass', f'pass:{passphrase}'],
        capture_output=True, text=True, timeout=60
    )
    if r.returncode != 0:
        print(f'ERROR: Decryption failed: {r.stderr}')
        sys.exit(1)

    # Extract
    r = subprocess.run(
        ['tar', 'xzf', str(tar_path), '-C', str(dest_dir)],
        capture_output=True, text=True, timeout=60
    )
    if r.returncode != 0:
        print(f'ERROR: Extraction failed: {r.stderr}')
        sys.exit(1)

    tar_path.unlink()
    return dest_dir

def list_contents(enc_path):
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        decrypt_archive(enc_path, tmpdir)

        print(f'\nContents of {enc_path.name}:')
        print()
        for fp in sorted(tmpdir.rglob('*')):
            if fp.is_file():
                rel = fp.relative_to(tmpdir)
                size = fp.stat().st_size / 1024
                print(f'  {rel}  ({size:.1f} KB)')

def restore(enc_path, dry_run=False):
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        decrypt_archive(enc_path, tmpdir)

        # Find all .db and .sqlite files
        db_files = list(tmpdir.rglob('*.db')) + list(tmpdir.rglob('*.sqlite'))

        if not db_files:
            print('No database files found in backup.')
            return

        print(f'\nRestoring {len(db_files)} database(s) from {enc_path.name}:')
        print()

        for db in db_files:
            rel = db.relative_to(tmpdir)
            dest = ROOT / rel

            if dry_run:
                exists = '(overwrite)' if dest.exists() else '(new)'
                print(f'  [DRY RUN] {rel} → {dest} {exists}')
                continue

            # Create backup of current file before overwriting
            if dest.exists():
                pre_restore = dest.with_suffix(dest.suffix + '.pre_restore')
                shutil.copy2(dest, pre_restore)
                print(f'  Backed up current: {dest.name} → {pre_restore.name}')

            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(db, dest)
            print(f'  ✅ Restored: {rel}')

        if not dry_run:
            print(f'\nRestore complete. Pre-restore copies saved with .pre_restore suffix.')
            print('To undo: rename .pre_restore files back to original names.')

def main():
    args = sys.argv[1:]

    if not args:
        list_backups()
        print('\nUsage:')
        print('  python3 restore_databases.py latest')
        print('  python3 restore_databases.py <filename>')
        print('  python3 restore_databases.py <filename> --list')
        print('  python3 restore_databases.py <filename> --dry-run')
        return

    target = args[0]
    flags = args[1:]

    # Resolve target
    if target == 'latest':
        backups = sorted(BACKUP_DIR.glob('db_backup_*.tar.gz.enc'))
        if not backups:
            print('No backups found.')
            return
        enc_path = backups[-1]
    elif (BACKUP_DIR / target).exists():
        enc_path = BACKUP_DIR / target
    else:
        # Try as index
        try:
            idx = int(target) - 1
            backups = sorted(BACKUP_DIR.glob('db_backup_*.tar.gz.enc'))
            enc_path = backups[idx]
        except (ValueError, IndexError):
            print(f'Backup not found: {target}')
            return

    if '--list' in flags:
        list_contents(enc_path)
    elif '--dry-run' in flags:
        restore(enc_path, dry_run=True)
    else:
        print(f'Restoring from: {enc_path.name}')
        confirm = input('Continue? (y/N): ').strip().lower()
        if confirm == 'y':
            restore(enc_path)
        else:
            print('Cancelled.')

if __name__ == '__main__':
    main()
