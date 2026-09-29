#!/bin/bash
set -euo pipefail

python - <<'PY'
from pathlib import Path
Path('/workspace/config.env').write_text('BACKEND_URL=http://127.0.0.1:8000\n', encoding='utf-8')
PY
printf '%s\n' 'Backend URL repaired to local service endpoint.'
