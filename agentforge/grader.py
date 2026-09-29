from __future__ import annotations

import json
import re
import time

from agentforge.config import TASKS_ROOT, load_task_spec
from agentforge.docker_utils import build_image, find_active_task_container, run_command
from agentforge.models import EvaluationResult


def parse_json_payload(stdout: str) -> dict | None:
    if not stdout:
        return None
    match = re.search(r"\{.*\}", stdout, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    try:
        return json.loads(stdout.strip())
    except json.JSONDecodeError:
        return None


def grade_task(task_id: str, image_name: str | None = None, *, command: str | None = None, timeout: int | None = None, container_name: str | None = None) -> EvaluationResult:
    spec = load_task_spec(task_id)
    if command is None:
        command = spec.test_command
    if container_name is None:
        container_name = find_active_task_container(task_id)
    if image_name is None and container_name is None:
        image_name = build_image(TASKS_ROOT / task_id, task_id)
    start = time.time()
    if container_name is not None:
        docker_cmd = ["docker", "exec", container_name, "bash", "-lc", command]
        result = run_command(docker_cmd, capture_output=True, timeout=timeout or spec.timeout_seconds, check=False)
    else:
        docker_cmd = [
            "docker",
            "run",
            "--rm",
            "--label",
            "agentforge.managed=true",
            "--label",
            f"agentforge.task={task_id}",
            "--entrypoint",
            "bash",
            image_name,
            "-lc",
            command,
        ]
        result = run_command(docker_cmd, capture_output=True, timeout=timeout or spec.timeout_seconds, check=False)
    duration = time.time() - start
    payload = parse_json_payload(result.stdout)
    tests_total = 0
    tests_passed = 0
    success = result.returncode == 0
    error_category = "SUCCESS" if success else "TEST_FAILURE"
    if payload and isinstance(payload, dict):
        tests_total = int(payload.get("total", payload.get("tests_total", 0) or 0))
        tests_passed = int(payload.get("passed", payload.get("tests_passed", 0) or 0))
        success = bool(payload.get("success", success))
        error_category = "SUCCESS" if success else "TEST_FAILURE"
    if tests_total == 0 and result.returncode == 0:
        tests_total = 1
        tests_passed = 1
    elif tests_total == 0 and result.returncode != 0:
        tests_total = 1
        tests_passed = 0

    return EvaluationResult(
        task_id=task_id,
        success=bool(success),
        tests_passed=tests_passed,
        tests_total=tests_total,
        duration_seconds=round(duration, 3),
        exit_code=result.returncode,
        stdout=result.stdout,
        stderr=result.stderr,
        error_category=error_category,
        notes="Evaluation completed.",
    )
