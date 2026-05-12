#!/bin/bash
set -e
mkdir -p agents/admin agents/worker_fetcher agents/worker_extractor agents/worker_planner workspace command_outputs credentials logs
touch workspace/tasks.jsonl workspace/forwarded_messages.jsonl workspace/pending_commands.jsonl
if [ ! -p workspace/REDACTED ]; then
  mkfifo workspace/REDACTED || true
fi
chmod 600 workspace/REDACTED || true
chmod 700 credentials || true
echo 'Setup complete.'
