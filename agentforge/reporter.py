from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from agentforge.config import REPORTS_ROOT
from agentforge.models import EvaluationResult


def build_report(task_id: str, result: EvaluationResult, *, extra: dict | None = None) -> dict:
    payload = {
        "task_id": task_id,
        "success": result.success,
        "tests_passed": result.tests_passed,
        "tests_total": result.tests_total,
        "duration_seconds": result.duration_seconds,
        "exit_code": result.exit_code,
        "error_category": result.error_category,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "notes": result.notes,
    }
    if extra:
        payload.update(extra)
    return payload


def write_report(task_id: str, result: EvaluationResult, *, extra: dict | None = None) -> tuple[Path, Path]:
    REPORTS_ROOT.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    json_path = REPORTS_ROOT / f"{task_id}-{stamp}.json"
    md_path = REPORTS_ROOT / f"{task_id}-{stamp}.md"
    payload = build_report(task_id, result, extra=extra)

    with json_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")

    with md_path.open("w", encoding="utf-8") as handle:
        handle.write(f"# {task_id}\n\n")
        handle.write(f"- Success: {result.success}\n")
        handle.write(f"- Tests: {result.tests_passed}/{result.tests_total}\n")
        handle.write(f"- Exit code: {result.exit_code}\n")
        handle.write(f"- Duration: {result.duration_seconds} sec\n")
        handle.write(f"- Error category: {result.error_category}\n\n")
        handle.write("## stdout\n\n")
        handle.write(result.stdout or "(empty)\n")
        if result.stderr:
            handle.write("\n\n## stderr\n\n")
            handle.write(result.stderr)

    return json_path, md_path
