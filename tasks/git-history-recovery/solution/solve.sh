#!/bin/bash
set -euo pipefail
cd /workspace/repo
LOST_SHA=$(git reflog --format='%H %gs' | awk '/recover-critical-data/ {print $1; exit}')
if [ -z "$LOST_SHA" ]; then
  echo 'Lost commit not found in reflog.' >&2
  exit 1
fi

git reset --hard "$LOST_SHA"
printf '%s\n' 'Recovered the lost git commit from reflog history.'
