#!/bin/bash
set -e
mkdir -p agents/admin agents/worker_fetcher agents/worker_extractor agents/worker_planner workspace command_outputs credentials logs
touch workspace/tasks.jsonl workspace/forwarded_messages.jsonl workspace/pending_commands.jsonl
if [ ! -p workspace/command_approver_fifo ]; then
  mkfifo workspace/command_approver_fifo || true
fi
chmod 600 workspace/command_approver_fifo || true
chmod 700 credentials || true
echo 'Setup complete.'
