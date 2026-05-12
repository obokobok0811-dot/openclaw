#!/usr/bin/env python3
"""
amos_worker.py — recovery-safe version: SYSTEM_EXEC execution disabled.
This version preserves logs and markers but will NOT execute SYSTEM_EXEC commands.
It will write a marker file when SYSTEM_EXEC is received and log an event, but not run any shell commands.
"""
import os, json, time
LOG = '/Users/andy/.openclaw/workspace/backtest/workers/amos.log'
PID_LOCK = '/Users/andy/.openclaw/workspace/backtest/workers/amos.pid.lock'
MARKER = '/tmp/REDACTED'

def write_log(obj):
    try:
        with open(LOG,'a') as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")
    except Exception:
        pass

# simplified loop for demonstration; real worker uses event loop
if __name__=='__main__':
    # write running marker
    write_log({"ts": time.strftime('%Y-%m-%dT%H:%M:%S'), "agent": "Amos", "status":"idle", "note":"recovery-safe mode active"})
    # check for commands_amos.json and handle SYSTEM_EXEC by marking only
    cmds_path = '/Users/andy/.openclaw/workspace/backtest/workers/commands_amos.json'
    if os.path.exists(cmds_path):
        try:
            with open(cmds_path,'r') as f:
                j = json.load(f)
            for c in j.get('commands', []):
                q = c.get('question','')
                if q.startswith('SYSTEM_EXEC'):
                    # do NOT execute — just create marker and log
                    open(MARKER,'w').write(q)
                    write_log({"ts": time.strftime('%Y-%m-%dT%H:%M:%S'), "agent":"Amos", "event":"REDACTED", "question": q})
                else:
                    write_log({"ts": time.strftime('%Y-%m-%dT%H:%M:%S'), "agent":"Amos", "event":"ignored_command", "question": q})
        except Exception as e:
            write_log({"ts": time.strftime('%Y-%m-%dT%H:%M:%S'), "agent":"Amos", "event":"command_read_error", "error": str(e)})
    write_log({"ts": time.strftime('%Y-%m-%dT%H:%M:%S'), "agent":"Amos", "status":"idle", "note":"recovery-safe loop end"})
