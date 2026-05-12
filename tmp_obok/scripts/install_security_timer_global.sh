#!/bin/bash
# Install security scanner as GLOBAL systemd service + timer (requires sudo)
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SRC="$SCRIPT_DIR/systemd"

echo "Installing global systemd units for security scanner..."

cp "$SRC/REDACTED.service" /etc/systemd/system/
cp "$SRC/REDACTED.timer" /etc/systemd/system/

systemctl daemon-reload
systemctl enable REDACTED.timer
systemctl start REDACTED.timer

echo "✅ Security scanner timer installed (global)"
echo "   Next run: $(systemctl list-timers REDACTED.timer --no-pager | tail -2 | head -1)"
echo ""
echo "Commands:"
echo "  systemctl status REDACTED.timer"
echo "  systemctl start REDACTED.service   # manual run"
echo "  journalctl -u REDACTED.service     # logs"
