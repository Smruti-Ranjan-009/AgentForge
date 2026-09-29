from __future__ import annotations

import json
import time
from pathlib import Path
from uuid import uuid4

from agentforge.config import TASKS_ROOT, load_task_spec
from agentforge.docker_utils import NETWORKED_TASK_ID, build_image, cleanup_agentforge_resources, ensure_docker_available, run_command, start_task_container
from agentforge.exceptions import EvaluationError, TaskConfigError
from agentforge.grader import grade_task
from agentforge.models import EvaluationResult, ValidationReport, ValidationStep


def validate_task(task_id: str, *, verbose: bool = False) -> ValidationReport:
    task_dir = TASKS_ROOT / task_id
    steps: list[ValidationStep] = []

    if not task_dir.exists():
        raise TaskConfigError(f"Task directory does not exist: {task_dir}")
    steps.append(ValidationStep(name="task directory", success=True, detail=f"Found {task_dir}"))

    task_yaml = task_dir / "task.yaml"
    if not task_yaml.exists():
        raise TaskConfigError(f"Missing task.yaml for {task_id}")
    steps.append(ValidationStep(name="task.yaml", success=True, detail=f"Found {task_yaml}"))

    try:
        spec = load_task_spec(task_id)
    except Exception as exc:  # noqa: BLE001
        raise TaskConfigError(str(exc)) from exc
    steps.append(ValidationStep(name="schema valid", success=True, detail=f"Loaded task '{spec.title}'"))

    required_files = [
        task_dir / "instruction.md",
        task_dir / "environment" / "Dockerfile",
        task_dir / "tests" / "test.sh",
        task_dir / "solution" / "solve.sh",
    ]
    missing = [str(path.relative_to(task_dir)) for path in required_files if not path.exists()]
    if missing:
        raise TaskConfigError(f"Missing required files for {task_id}: {', '.join(missing)}")
    steps.append(ValidationStep(name="required files", success=True, detail="All task files present"))

    dockerfile = task_dir / "environment" / "Dockerfile"
    if not dockerfile.exists():
        raise TaskConfigError(f"Dockerfile is missing for {task_id}")
    steps.append(ValidationStep(name="Dockerfile", success=True, detail=f"Found {dockerfile}"))

    image_name = build_image(task_dir, task_id, verbose=verbose)
    steps.append(ValidationStep(name="image builds", success=True, detail=f"Built {image_name}"))

    if task_id == NETWORKED_TASK_ID:
        container_name = start_task_container(task_id, image_name)
        steps.append(ValidationStep(name="backend and isolated network started", success=True, detail="Client and backend are running on the managed Docker network"))
    else:
        container_name = f"agentforge-{task_id}-{uuid4().hex[:8]}"
        run_cmd = [
            "docker",
            "run",
            "-d",
            "--name",
            container_name,
            "--label",
            "agentforge.managed=true",
            "--label",
            f"agentforge.task={task_id}",
            image_name,
            "bash",
            "-lc",
            "sleep 600",
        ]
        container_start = run_command(run_cmd, capture_output=True, check=False)
        if container_start.returncode != 0:
            raise EvaluationError(f"Failed to launch validation container for {task_id}: {container_start.stderr or container_start.stdout}")

    try:
        initial = run_command(["docker", "exec", container_name, "bash", "-lc", spec.test_command], capture_output=True, check=False, timeout=spec.timeout_seconds)
        if initial.returncode == 0:
            raise EvaluationError(f"Broken state validation failed: {task_id} already passes before the fix.")
        steps.append(ValidationStep(name="broken state confirmed", success=True, detail=f"Test failed as expected with exit code {initial.returncode}"))

        reference = run_command(["docker", "exec", container_name, "bash", "-lc", spec.solution_command], capture_output=True, check=False, timeout=spec.timeout_seconds)
        if reference.returncode != 0:
            raise EvaluationError(f"Reference solution execution failed for {task_id}: {reference.stderr or reference.stdout}")
        steps.append(ValidationStep(name="reference solution executed", success=True, detail="Reference fix applied successfully"))

        post = run_command(["docker", "exec", container_name, "bash", "-lc", spec.test_command], capture_output=True, check=False, timeout=spec.timeout_seconds)
        if post.returncode != 0:
            raise EvaluationError(f"Post-solution tests failed for {task_id}: {post.stderr or post.stdout}")
        steps.append(ValidationStep(name="post-solution tests passed", success=True, detail=f"Exit code {post.returncode}"))
    finally:
        if task_id != NETWORKED_TASK_ID:
            run_command(["docker", "rm", "-f", container_name], capture_output=True, check=False)

    cleanup_agentforge_resources()
    steps.append(ValidationStep(name="cleanup successful", success=True, detail="AgentForge resources removed"))
    return ValidationReport(task_id=task_id, valid=True, steps=steps, message="Task valid.")


def validate_all_tasks() -> dict[str, ValidationReport]:
    report: dict[str, ValidationReport] = {}
    for task_id in sorted([p.name for p in TASKS_ROOT.iterdir() if p.is_dir()]):
        try:
            report[task_id] = validate_task(task_id)
        except Exception as exc:  # noqa: BLE001
            report[task_id] = ValidationReport(task_id=task_id, valid=False, message=str(exc))
    return report
