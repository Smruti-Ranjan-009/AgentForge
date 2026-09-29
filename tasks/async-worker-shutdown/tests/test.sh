#!/bin/bash
set -euo pipefail
python - <<'PY'
import asyncio
import json
from worker import run_worker

async def run_check():
    result = await run_worker()
    if result["pending"] != 0:
        raise AssertionError(f"pending tasks remain: {result}")
    if result["status"] != "cancelled":
        raise AssertionError(f"unexpected shutdown result: {result}")
    print(json.dumps({"passed": 1, "total": 1, "success": True, "detail": "shutdown state clean"}))

asyncio.run(run_check())
PY
