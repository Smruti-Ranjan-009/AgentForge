#!/bin/bash
set -euo pipefail
cat > /workspace/ci.sh <<'EOF'
#!/bin/bash
set -euo pipefail
cd /workspace
pytest -q tests/test_app.py
EOF
chmod +x /workspace/ci.sh
printf '%s\n' 'CI script corrected to run from the workspace root.'
