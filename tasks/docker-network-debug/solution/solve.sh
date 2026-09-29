#!/bin/bash
set -euo pipefail

printf '%s\n' 'BACKEND_URL=http://backend:8000' > /workspace/config.env
printf '%s\n' 'Backend URL repaired to the Docker service endpoint.'
