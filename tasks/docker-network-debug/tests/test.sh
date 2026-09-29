#!/bin/bash
set -euo pipefail

source /workspace/config.env
export BACKEND_URL

python - <<'PY'
import json
import os
import urllib.request

url = os.environ["BACKEND_URL"]
try:
    response = urllib.request.urlopen(url, timeout=5).read().decode("utf-8")
except Exception as exc:  # pragma: no cover
    print(json.dumps({"passed": 0, "total": 1, "success": False, "detail": str(exc)}))
    raise SystemExit(1)

if response != "AgentForge backend is healthy.":
    print(json.dumps({"passed": 0, "total": 1, "success": False, "detail": "backend response did not match the expected payload"}))
    raise SystemExit(1)

print(json.dumps({"passed": 1, "total": 1, "success": True, "detail": "backend responded successfully"}))
PY
