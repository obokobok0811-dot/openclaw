#!/bin/bash
# Install security scanner as systemd --user service + timer
set -e

UNIT_DIR="$HOME/.config/systemd/user"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SRC="$SCRIPT_DIR/systemd"

mkdir -p "$UNIT_DIR"

cp "$SRC/REDACTED.service" "$UNIT_DIR/"
cp "$SRC/REDACTED.timer" "$UNIT_DIR/"

# user-level units don't need User= directive
sed -i '' '/^User=/d' "$UNIT_DIR/REDACTED.service" 2>/dev/null || true

systemctl --user daemon-reload
systemctl --user enable REDACTED.timer
systemctl --user start REDACTED.timer

echo "✅ Security scanner timer installed (user-level)"
echo "   Next run: $(systemctl --user list-timers REDACTED.timer --no-pager | tail -2 | head -1)"
echo ""
echo "Commands:"
echo "  systemctl --user status REDACTED.timer"
echo "  systemctl --user start REDACTED.service   # manual run"
echo "  journalctl --user -u REDACTED.service     # logs"
