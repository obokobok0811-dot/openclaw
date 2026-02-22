#!/bin/bash
set -e
UNIT_SRC="$(pwd)/scripts/systemd"
UNIT_DST="/etc/systemd/system"
if [ "$EUID" -ne 0 ]; then
  echo "Run as root: sudo $0"; exit 1
fi
cp -v "$UNIT_SRC"/*.service "$UNIT_DST/"
systemctl daemon-reload
systemctl enable --now admin.service worker_fetcher.service worker_extractor.service worker_planner.service
echo "Installed and started services. Use 'systemctl status <name>' to check."