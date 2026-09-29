#!/bin/bash
set -euo pipefail
python - <<'PY'
import json
try:
    from app import ServiceConfig
except Exception as exc:  # pragma: no cover
    print(json.dumps({"passed": 0, "total": 1, "success": False, "detail": str(exc)}))
    raise SystemExit(1)
config = ServiceConfig(name='agentforge')
assert config.name == 'agentforge'
print(json.dumps({"passed": 1, "total": 1, "success": True, "detail": "dependency configuration restored"}))
PY
