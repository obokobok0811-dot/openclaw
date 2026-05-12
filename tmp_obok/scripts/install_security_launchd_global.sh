#!/bin/bash
# Install security scanner as macOS LaunchDaemon (GLOBAL, requires sudo)
set -e

PLIST_NAME="com.clawd.security-scanner.plist"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SRC="$SCRIPT_DIR/launchd/$PLIST_NAME"
DEST="/Library/LaunchDaemons/$PLIST_NAME"

echo "Installing global LaunchDaemon for security scanner..."
echo "(Requires sudo)"

# Unload if already loaded
sudo launchctl unload "$DEST" 2>/dev/null || true

sudo cp "$SRC" "$DEST"
sudo chown root:wheel "$DEST"
sudo chmod 644 "$DEST"
sudo launchctl load "$DEST"

echo "✅ Security scanner LaunchDaemon installed (global)"
echo "   Runs daily at 03:30"
echo ""
echo "Commands:"
echo "  sudo launchctl list | grep clawd                     # check status"
echo "  sudo launchctl start com.clawd.security-scanner      # manual run"
echo "  sudo launchctl unload /Library/LaunchDaemons/$PLIST_NAME  # disable"
echo "  cat poc/security/launchd_stdout.log                  # view output"
