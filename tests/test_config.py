from pathlib import Path

import pytest

from agentforge.config import load_task_spec, load_yaml
from agentforge.exceptions import TaskConfigError, TaskNotFoundError


def test_load_task_spec_valid():
    spec = load_task_spec("docker-network-debug")
    assert spec.id == "docker-network-debug"
    assert spec.category == "docker"
    assert spec.environment["dockerfile"] == "environment/Dockerfile"


def test_missing_task_raises():
    with pytest.raises(TaskNotFoundError):
        load_task_spec("not-a-real-task")


def test_invalid_yaml_raises(tmp_path):
    bad_file = tmp_path / "broken.yaml"
    bad_file.write_text("id: [broken\n", encoding="utf-8")
    with pytest.raises(TaskConfigError):
        load_yaml(bad_file)


def test_invalid_task_schema_raises(tmp_path):
    invalid_task_dir = tmp_path / "broken-task"
    invalid_task_dir.mkdir()
    (invalid_task_dir / "task.yaml").write_text("id: bad\ndifficulty: impossible\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_task_spec("broken-task", tasks_root=tmp_path)
