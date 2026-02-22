#!/usr/bin/env python3
"""Simple memory search wrapper: search memory/qmd/*.qmd first, then MEMORY.md
Usage: tools/memory_search.py <query>
"""
import sys
import glob
import subprocess

if len(sys.argv) < 2:
    print("Usage: memory_search.py <query>")
    sys.exit(1)

query = sys.argv[1]

# Search qmd files
qmd_files = glob.glob('memory/qmd/*.qmd')
for f in qmd_files:
    with open(f, 'r', encoding='utf-8') as fh:
        content = fh.read()
        if query.lower() in content.lower():
            print(f"Found in {f}:\n")
            # print small excerpt
            idx = content.lower().find(query.lower())
            start = max(0, idx-120)
            end = min(len(content), idx+120)
            print(content[start:end].replace('\n', ' '))
            print('\n---\n')

# Fallback to MEMORY.md
try:
    with open('MEMORY.md','r', encoding='utf-8') as fh:
        content = fh.read()
        if query.lower() in content.lower():
            print('Found in MEMORY.md:\n')
            idx = content.lower().find(query.lower())
            start = max(0, idx-120)
            end = min(len(content), idx+120)
            print(content[start:end].replace('\n',' '))
except FileNotFoundError:
    pass
