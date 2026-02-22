#!/bin/bash
# Install security scanner as GLOBAL systemd service + timer (requires sudo)
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SRC="$SCRIPT_DIR/systemd"

echo "Installing global systemd units for security scanner..."

cp "$SRC/clawd-security-scanner.service" /etc/systemd/system/
cp "$SRC/clawd-security-scanner.timer" /etc/systemd/system/

systemctl daemon-reload
systemctl enable clawd-security-scanner.timer
systemctl start clawd-security-scanner.timer

echo "✅ Security scanner timer installed (global)"
echo "   Next run: $(systemctl list-timers clawd-security-scanner.timer --no-pager | tail -2 | head -1)"
echo ""
echo "Commands:"
echo "  systemctl status clawd-security-scanner.timer"
echo "  systemctl start clawd-security-scanner.service   # manual run"
echo "  journalctl -u clawd-security-scanner.service     # logs"
