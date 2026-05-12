#!/bin/zsh
mkdir -p /Users/andy/.openclaw/workspace/tools
touch /Users/andy/.openclaw/workspace/tools/__init__.py
cd /Users/andy/.openclaw/workspace
PYTHONPATH=/Users/andy/.openclaw/workspace python3 auto_trader.py
