from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from typer.testing import CliRunner

from agentforge.cli import app
from agentforge.docker_utils import cleanup_agentforge_resources, run_command
from agentforge.exceptions import EvaluationError
from agentforge.grader import grade_task
from agentforge.models import EvaluationResult
from agentforge.runner import TaskRunner

runner = CliRunner()


def test_run_command_uses_utf8_decoding(mocker):
    called = {}

    def fake_run(command, **kwargs):
        called["command"] = command
        called["kwargs"] = kwargs
        return SimpleNamespace(returncode=0, stdout="ok", stderr="")

    mocker.patch("subprocess.run", side_effect=fake_run)
    run_command(["docker", "info"], capture_output=True)

    assert called["kwargs"]["text"] is True
    assert called["kwargs"]["encoding"] == "utf-8"
    assert called["kwargs"]["errors"] == "replace"


def test_grade_without_active_environment(mocker):
    task = TaskRunner("docker-network-debug")
    mocker.patch("agentforge.runner.find_active_task_container", return_value=None)
    try:
        task.grade()
        assert False, "Expected EvaluationError when no active environment exists"
    except EvaluationError as exc:
        assert "No active environment found for docker-network-debug" in str(exc)
        assert "agentforge run docker-network-debug" in str(exc)


def test_run_and_grade_reuse_same_active_container(mocker):
    task = TaskRunner("docker-network-debug")
    calls: list[str] = []
    mocker.patch("agentforge.runner.find_active_task_container", side_effect=["agentforge-docker-network-debug", "agentforge-docker-network-debug"])
    mocker.patch("agentforge.runner.run_command", side_effect=lambda command, **kwargs: (calls.append(command[0]) or SimpleNamespace(returncode=0, stdout="{\"passed\": 1, \"total\": 1, \"success\": true}", stderr="")))

    task.run_task(interactive=True)
    result = task.grade()

    assert result.returncode == 0
    assert calls[0] == "docker"


def test_interactive_shell_ignores_task_timeout(mocker):
    task = TaskRunner("docker-network-debug")
    mocker.patch("agentforge.runner.find_active_task_container", return_value="agentforge-docker-network-debug")
    seen = {}

    def fake_run_command(command, **kwargs):
        seen["command"] = command
        seen["kwargs"] = kwargs
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    mocker.patch("agentforge.runner.run_command", side_effect=fake_run_command)
    task.run_task(interactive=True)

    assert seen["command"][:4] == ["docker", "exec", "-it", "agentforge-docker-network-debug"]
    assert seen["kwargs"].get("timeout") is None
    assert seen["kwargs"].get("interactive") is True


def test_report_command_successful_exit(mocker):
    fake_result = EvaluationResult(
        task_id="docker-network-debug",
        success=True,
        tests_passed=1,
        tests_total=1,
        duration_seconds=0.1,
        exit_code=0,
        stdout="{\"passed\": 1, \"total\": 1, \"success\": true}",
        stderr="",
        notes="ok",
    )
    mocker.patch("agentforge.cli.find_active_task_container", return_value="agentforge-docker-network-debug")
    mocker.patch("agentforge.cli.grade_task", return_value=fake_result)
    mocker.patch("agentforge.cli.write_report", return_value=(Path("reports/docker-network-debug.json"), Path("reports/docker-network-debug.md")))

    result = runner.invoke(app, ["report", "docker-network-debug"])

    assert result.exit_code == 0
    assert "Report written to" in result.stdout
    assert "Markdown report written to" in result.stdout
    assert "Failed to generate report" not in result.stdout


def test_cleanup_removes_running_managed_container():
    container_name = f"agentforge-cleanup-test-{uuid4().hex[:8]}"
    run_result = run_command(
        [
            "docker",
            "run",
            "-d",
            "--name",
            container_name,
            "--label",
            "agentforge.managed=true",
            "alpine:latest",
            "sh",
            "-lc",
            "while true; do sleep 60; done",
        ],
        capture_output=True,
        check=False,
    )
    if run_result.returncode != 0:
        pytest.skip("Docker is unavailable or alpine image could not be started for cleanup regression test.")

    try:
        pre_cleanup = run_command(
            [
                "docker",
                "ps",
                "-a",
                "--filter",
                "label=agentforge.managed=true",
                "--filter",
                f"name={container_name}",
                "--format",
                "{{.Names}}",
            ],
            capture_output=True,
            check=False,
        )
        assert container_name in pre_cleanup.stdout

        cleanup_agentforge_resources()

        post_cleanup = run_command(
            [
                "docker",
                "ps",
                "-a",
                "--filter",
                "label=agentforge.managed=true",
                "--filter",
                f"name={container_name}",
                "--format",
                "{{.Names}}",
            ],
            capture_output=True,
            check=False,
        )
        assert post_cleanup.stdout.strip() == ""
    finally:
        run_command(["docker", "rm", "-f", container_name], capture_output=True, check=False)
