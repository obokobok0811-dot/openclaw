#!/bin/bash
set -e
if [ -z "$VIRTUAL_ENV" ]; then
  python3 -m venv .venv
  source .venv/bin/activate
fi
python -m pip install --upgrade pip
pip install -r poc/requirements.txt
# create db
mkdir -p poc/data poc/vectors poc/db
sqlite3 poc/crm.db < poc/db/schema.sql || true
echo 'PoC setup complete. Place credentials in workspace/credentials/ and run collectors.'
