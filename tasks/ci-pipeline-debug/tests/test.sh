#!/bin/bash
set -euo pipefail
bash /workspace/ci.sh
python - <<'PY'
import json
print(json.dumps({"passed": 1, "total": 1, "success": True, "detail": "ci validation passed"}))
PY
