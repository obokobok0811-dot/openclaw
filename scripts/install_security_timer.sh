#!/bin/bash
# Install security scanner as systemd --user service + timer
set -e

UNIT_DIR="$HOME/.config/systemd/user"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SRC="$SCRIPT_DIR/systemd"

mkdir -p "$UNIT_DIR"

cp "$SRC/clawd-security-scanner.service" "$UNIT_DIR/"
cp "$SRC/clawd-security-scanner.timer" "$UNIT_DIR/"

# user-level units don't need User= directive
sed -i '' '/^User=/d' "$UNIT_DIR/clawd-security-scanner.service" 2>/dev/null || true

systemctl --user daemon-reload
systemctl --user enable clawd-security-scanner.timer
systemctl --user start clawd-security-scanner.timer

echo "✅ Security scanner timer installed (user-level)"
echo "   Next run: $(systemctl --user list-timers clawd-security-scanner.timer --no-pager | tail -2 | head -1)"
echo ""
echo "Commands:"
echo "  systemctl --user status clawd-security-scanner.timer"
echo "  systemctl --user start clawd-security-scanner.service   # manual run"
echo "  journalctl --user -u clawd-security-scanner.service     # logs"
