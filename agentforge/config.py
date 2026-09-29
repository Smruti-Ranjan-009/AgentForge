from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from agentforge.exceptions import TaskConfigError, TaskNotFoundError
from agentforge.models import TaskSpec

REPO_ROOT = Path(__file__).resolve().parent.parent
TASKS_ROOT = REPO_ROOT / "tasks"
REPORTS_ROOT = REPO_ROOT / "reports"


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
    except FileNotFoundError as exc:  # pragma: no cover - defensive
        raise TaskConfigError(f"Task file not found: {path}") from exc
    except yaml.YAMLError as exc:  # pragma: no cover - defensive
        raise TaskConfigError(f"Invalid YAML in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise TaskConfigError(f"Task configuration at {path} must contain a mapping at the top level.")
    return data


def discover_task_ids(tasks_root: Path | None = None) -> list[str]:
    root = tasks_root or TASKS_ROOT
    if not root.exists():
        return []
    return sorted([p.name for p in root.iterdir() if p.is_dir()])


def load_task_spec(task_id: str, tasks_root: Path | None = None) -> TaskSpec:
    root = tasks_root or TASKS_ROOT
    task_dir = root / task_id
    if not task_dir.exists():
        raise TaskNotFoundError(task_id)
    config_path = task_dir / "task.yaml"
    if not config_path.exists():
        raise TaskConfigError(f"Task '{task_id}' is missing task.yaml")
    raw = load_yaml(config_path)
    spec = TaskSpec.model_validate({"id": task_id, **raw})
    return spec


def list_task_specs(tasks_root: Path | None = None) -> list[TaskSpec]:
    return [load_task_spec(task_id, tasks_root) for task_id in discover_task_ids(tasks_root)]


def write_json_report(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
