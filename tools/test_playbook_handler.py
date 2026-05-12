#!/usr/bin/env python3
from pathlib import Path
import subprocess
from datetime import datetime
from pathlib import Path
append = lambda m: Path('/Users/andy/.openclaw/workspace/auto_trader_debug.log').write_text(Path('/Users/andy/.openclaw/workspace/auto_trader_debug.log').read_text()+m+'\n') if Path('/Users/andy/.openclaw/workspace/auto_trader_debug.log').exists() else Path('/Users/andy/.openclaw/workspace/auto_trader_debug.log').write_text(m+'\n')

append(f"PLAYBOOK_TEST_START {datetime.now().isoformat()}")
playbook_dir = Path('/Users/andy/Documents/Obsidian/Obsidian Vault/OpenClaw')
candidates = []
for p in playbook_dir.rglob('*.md'):
    try:
        t = p.read_text()
        if '#error_playbook' in t:
            candidates.append(p)
    except Exception:
        continue
for pb in candidates:
    txt = pb.read_text()
    import re
    cmds = re.findall(r'^(?:CMD:|```bash\n)(.+?)(?:\n```|$)', txt, flags=re.DOTALL | re.MULTILINE)
    more = re.findall(r'^\$\s*(.+)$', txt, flags=re.MULTILINE)
    for c in more:
        cmds.append(c)
    for cmd in cmds:
        try:
            append(f"PLAYBOOK_EXEC {pb.name} -> {cmd.strip()} {datetime.now().isoformat()}")
            # simulated execution log
            append(f"SIMULATED_EXEC: {cmd.strip()}")
        except Exception as ee:
            append(f"PLAYBOOK_CMD_FAIL {cmd.strip()} -> {ee}")
append(f"PLAYBOOK_TEST_END {datetime.now().isoformat()}")
print('done')
