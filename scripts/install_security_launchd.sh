#!/bin/bash
# Install security scanner as macOS LaunchAgent (user-level, no sudo)
set -e

PLIST_NAME="com.clawd.security-scanner.plist"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SRC="$SCRIPT_DIR/launchd/$PLIST_NAME"
DEST="$HOME/Library/LaunchAgents/$PLIST_NAME"

mkdir -p "$HOME/Library/LaunchAgents"

# Unload if already loaded
launchctl unload "$DEST" 2>/dev/null || true

cp "$SRC" "$DEST"
launchctl load "$DEST"

echo "✅ Security scanner LaunchAgent installed"
echo "   Runs daily at 03:30"
echo ""
echo "Commands:"
echo "  launchctl list | grep clawd                    # check status"
echo "  launchctl start com.clawd.security-scanner     # manual run"
echo "  launchctl unload ~/Library/LaunchAgents/$PLIST_NAME  # disable"
echo "  cat poc/security/launchd_stdout.log            # view output"
