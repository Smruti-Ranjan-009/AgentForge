#!/bin/bash
set -euo pipefail
cd /workspace/repo
python - <<'PY'
import json, subprocess, sys

def run(cmd):
    return subprocess.run(cmd, shell=True, text=True, capture_output=True, check=False)

result = run('git rev-list --all --count')
if result.returncode != 0:
    print(json.dumps({"passed": 0, "total": 1, "success": False, "detail": "git repository not available"}))
    raise SystemExit(1)

log = run('git log --oneline --all')
if 'recover-critical-data' not in log.stdout:
    print(json.dumps({"passed": 0, "total": 1, "success": False, "detail": "recovery commit missing from history"}))
    raise SystemExit(1)

content = run('cat recovery.txt').stdout.strip()
if content != 'critical recovery data':
    print(json.dumps({"passed": 0, "total": 1, "success": False, "detail": f'unexpected recovered content: {content!r}'}))
    raise SystemExit(1)

print(json.dumps({"passed": 1, "total": 1, "success": True, "detail": "git history recovered"}))
PY
