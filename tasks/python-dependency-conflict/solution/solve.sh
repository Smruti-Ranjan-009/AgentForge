#!/bin/bash
set -euo pipefail
cat > /workspace/requirements.txt <<'EOF'
pydantic==2.9.2
fastapi==0.115.0
EOF
pip install --no-cache-dir -r /workspace/requirements.txt >/tmp/agentforge_dependency_fix.log 2>&1
python - <<'PY'
from pydantic import BaseModel, TypeAdapter

class ServiceConfig(BaseModel):
    name: str = 'agentforge'

adapter = TypeAdapter(ServiceConfig)
config = adapter.validate_python({'name': 'agentforge'})
print({'status': 'ok', 'name': config.name})
PY
printf '%s\n' 'Dependency mismatch resolved by pinning Pydantic 2.x.'
