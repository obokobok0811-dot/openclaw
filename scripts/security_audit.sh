#!/bin/bash
# security_audit.sh - quick security checklist for the OpenClaw workspace host
# Usage: bash scripts/security_audit.sh > security_report.txt
# Run locally (this script will not prompt for passwords). To include sudo checks, run with sudo.

OUT=security_report.txt
echo "OpenClaw Security Audit" > "$OUT"
echo "Generated: $(date -u) UTC" >> "$OUT"
echo "Host: $(hostname)" >> "$OUT"
echo "User: $(whoami)" >> "$OUT"
echo "" >> "$OUT"

WSPACE="$PWD"
CRED_DIR="$WSPACE/credentials"
WORKSPACE_DIR="$WSPACE/workspace"

echo "1) Credentials directory and permissions" >> "$OUT"
if [ -d "$CRED_DIR" ]; then
  ls -ld "$CRED_DIR" >> "$OUT"
  echo "Contents and perms:" >> "$OUT"
  ls -la "$CRED_DIR" >> "$OUT"
else
  echo "credentials/ directory not found" >> "$OUT"
fi
echo "" >> "$OUT"

echo "2) FIFO and pending commands" >> "$OUT"
if [ -p "$WORKSPACE_DIR/command_approver_fifo" ]; then
  echo "command_approver_fifo exists:" >> "$OUT"
  ls -l "$WORKSPACE_DIR/command_approver_fifo" >> "$OUT"
else
  echo "command_approver_fifo NOT FOUND" >> "$OUT"
fi
if [ -f "$WORKSPACE_DIR/pending_commands.jsonl" ]; then
  echo "pending_commands.jsonl perms:" >> "$OUT"
  ls -l "$WORKSPACE_DIR/pending_commands.jsonl" >> "$OUT"
  echo "Last 50 lines (if any):" >> "$OUT"
  tail -n 50 "$WORKSPACE_DIR/pending_commands.jsonl" >> "$OUT"
else
  echo "pending_commands.jsonl NOT FOUND" >> "$OUT"
fi
echo "" >> "$OUT"

echo "3) Workspace files with world-writable perms (danger)" >> "$OUT"
find "$WSPACE" -path "$WSPACE/.git" -prune -o -type f -perm -o+w -ls >> "$OUT" || true
echo "" >> "$OUT"

echo "4) Recent files modified in workspace (last 24h)" >> "$OUT"
find "$WSPACE" -type f -mtime -1 -ls | head -n 200 >> "$OUT" || true
echo "" >> "$OUT"

echo "5) Services (systemctl) status for admin/workers (requires sudo)" >> "$OUT"
if command -v systemctl >/dev/null 2>&1; then
  echo "(Attempting to query systemctl -- may require sudo)" >> "$OUT"
  if [ "$EUID" -eq 0 ]; then
    systemctl status admin.service --no-pager >> "$OUT" 2>&1 || true
    systemctl status worker_fetcher.service --no-pager >> "$OUT" 2>&1 || true
    systemctl status worker_extractor.service --no-pager >> "$OUT" 2>&1 || true
    systemctl status worker_planner.service --no-pager >> "$OUT" 2>&1 || true
  else
    echo "Not root; systemctl info not included. Re-run as sudo to include service statuses." >> "$OUT"
  fi
else
  echo "systemctl not available on this host" >> "$OUT"
fi
echo "" >> "$OUT"

echo "6) Listening network sockets (requires sudo for full info)" >> "$OUT"
if command -v lsof >/dev/null 2>&1; then
  if [ "$EUID" -eq 0 ]; then
    lsof -iTCP -sTCP:LISTEN -P -n >> "$OUT" 2>&1
  else
    echo "Run as root to list listening TCP sockets (lsof)." >> "$OUT"
  fi
elif command -v ss >/dev/null 2>&1; then
  if [ "$EUID" -eq 0 ]; then
    ss -tuln >> "$OUT" 2>&1
  else
    echo "Run as root to list listening sockets (ss)." >> "$OUT"
  fi
else
  echo "Neither lsof nor ss found; cannot list listening sockets." >> "$OUT"
fi
echo "" >> "$OUT"

echo "7) Check for known sensitive files in workspace (json, pem, key)" >> "$OUT"
find "$WSPACE" -type f \( -iname "*.key" -o -iname "*.pem" -o -iname "*.json" -o -iname "*secret*" -o -iname "*token*" \) -ls | head -n 200 >> "$OUT" || true
echo "(Note: json listing includes many harmless files; inspect manually for secrets)" >> "$OUT"
echo "" >> "$OUT"

echo "8) Docker containers (if docker available)" >> "$OUT"
if command -v docker >/dev/null 2>&1; then
  docker ps -a >> "$OUT" 2>&1
else
  echo "docker not found" >> "$OUT"
fi
echo "" >> "$OUT"

echo "9) Fail2ban status (if available)" >> "$OUT"
if command -v fail2ban-client >/dev/null 2>&1; then
  echo "fail2ban status:" >> "$OUT"
  fail2ban-client status >> "$OUT" 2>&1 || true
else
  echo "fail2ban not installed" >> "$OUT"
fi

echo "10) Suggested next steps" >> "$OUT"
echo "- If you have exposed tokens in this workspace, rotate/revoke them immediately." >> "$OUT"
echo "- Re-run this script as sudo to include system-wide service and socket checks." >> "$OUT"
echo "- Consider moving secrets to a secrets manager (Vault, GCP Secret Manager)." >> "$OUT"

echo "Security audit complete. Output: $OUT"
chmod 600 "$OUT" || true
