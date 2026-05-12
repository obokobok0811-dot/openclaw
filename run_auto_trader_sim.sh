#!/bin/zsh
# Safe wrapper to run recovery auto_trader in simulated mode
cd /Users/andy/.openclaw/workspace
export PYTHONPATH=/Users/andy/.openclaw/workspace
export SIMULATED=1
/usr/bin/python3 /Users/andy/.openclaw/workspace/auto_trader.recovery.py
