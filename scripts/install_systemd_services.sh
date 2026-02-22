#!/bin/bash
set -e
UNIT_DIR=~/.config/systemd/user
mkdir -p "$UNIT_DIR"
cp scripts/systemd/*.service "$UNIT_DIR/"
# Reload user systemd daemon
systemctl --user daemon-reload
# Enable and start services
systemctl --user enable --now admin.service
systemctl --user enable --now worker_fetcher.service
systemctl --user enable --now worker_extractor.service
systemctl --user enable --now worker_planner.service

echo "Services installed and started (user systemd). Use 'systemctl --user status <name>' to check."
