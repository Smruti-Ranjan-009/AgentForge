from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

from agentforge.exceptions import BuildError, DockerUnavailableError


def run_command(command: list[str], *, capture_output: bool = False, interactive: bool = False, cwd: str | None = None, timeout: int | None = None, check: bool = False) -> subprocess.CompletedProcess[str]:
    kwargs: dict[str, object] = {
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
        "check": check,
    }
    if not interactive and timeout is not None:
        kwargs["timeout"] = timeout
    if capture_output:
        kwargs["capture_output"] = True
    elif interactive:
        kwargs["stdin"] = sys.stdin
        kwargs["stdout"] = sys.stdout
        kwargs["stderr"] = sys.stderr
    else:
        kwargs["capture_output"] = True
    if cwd is not None:
        kwargs["cwd"] = cwd
    return subprocess.run(command, **kwargs)


def ensure_docker_available() -> None:
    if shutil.which("docker") is None:
        raise DockerUnavailableError("Docker CLI is not installed or not on PATH.")
    result = run_command(["docker", "info"], capture_output=True)
    if result.returncode != 0:
        raise DockerUnavailableError(f"Docker is unavailable: {result.stderr.strip() or result.stdout.strip() or 'unknown error'}")


def build_image(task_path: Path, task_id: str, *, verbose: bool = False) -> str:
    ensure_docker_available()
    image_name = f"agentforge-{task_id}:{uuid4().hex[:8]}"
    dockerfile = task_path / "environment" / "Dockerfile"
    if not dockerfile.exists():
        raise BuildError(f"Dockerfile missing for task '{task_id}' at {dockerfile}")

    command = [
        "docker",
        "build",
        "--label",
        "agentforge.managed=true",
        "--label",
        f"agentforge.task={task_id}",
        "-t",
        image_name,
        "-f",
        str(dockerfile),
        str(task_path),
    ]
    result = run_command(command, capture_output=not verbose, cwd=str(task_path))
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip() or "Unknown build failure"
        raise BuildError(f"Docker build failed for '{task_id}': {stderr}")
    return image_name


def _list_task_containers(task_id: str, *, include_stopped: bool = False) -> list[str]:
    docker_cmd = ["docker"]
    docker_cmd.extend(["ps", "-a"] if include_stopped else ["ps"])
    docker_cmd.extend(["--filter", "label=agentforge.managed=true", "--filter", f"label=agentforge.task={task_id}", "--format", "{{.Names}}"])
    result = run_command(docker_cmd, capture_output=True, check=False)
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def find_active_task_container(task_id: str) -> str | None:
    active = _list_task_containers(task_id)
    return active[0] if active else None


def start_task_container(task_id: str, image_name: str) -> str:
    ensure_docker_available()
    existing = _list_task_containers(task_id, include_stopped=True)
    active = _list_task_containers(task_id)
    if active:
        return active[0]
    for container_name in existing:
        run_command(["docker", "rm", "-f", container_name], capture_output=True, check=False)

    container_name = f"agentforge-{task_id}"
    run_command(
        [
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
            "while true; do sleep 60; done",
        ],
        capture_output=True,
        check=False,
    )
    return container_name


def run_container(image_name: str, task_id: str, *, command: list[str] | None = None, interactive: bool = False, timeout: int | None = None) -> subprocess.CompletedProcess[str]:
    ensure_docker_available()
    container_name = start_task_container(task_id, image_name)
    docker_cmd = ["docker", "exec", "-it" if interactive else "exec", container_name, "bash", "-lc"]
    if command is not None:
        docker_cmd = ["docker", "exec", "-it" if interactive else "exec", container_name, "bash", "-lc", " ".join(command)]
    if interactive:
        return run_command(docker_cmd, interactive=True)
    return run_command(docker_cmd, capture_output=True, timeout=timeout)


def cleanup_agentforge_resources() -> None:
    ensure_docker_available()
    label = "label=agentforge.managed=true"

    resource_specs = [
        ("container", ["docker", "ps", "-aq", "--filter", label], ["docker", "rm", "-f"]),
        ("network", ["docker", "network", "ls", "-q", "--filter", label], ["docker", "network", "rm"]),
        ("image", ["docker", "image", "ls", "-q", "--filter", label], ["docker", "rmi", "-f"]),
    ]

    failures: list[str] = []
    for resource_type, list_command, remove_prefix in resource_specs:
        list_result = run_command(list_command, capture_output=True, check=False)
        if list_result.returncode != 0:
            failures.append(
                f"Failed to list {resource_type}s: {list_result.stderr.strip() or list_result.stdout.strip() or 'unknown docker error'}"
            )
            continue

        for resource_id in [line.strip() for line in list_result.stdout.splitlines() if line.strip()]:
            remove_result = run_command([*remove_prefix, resource_id], capture_output=True, check=False)
            if remove_result.returncode != 0:
                failures.append(
                    f"Failed to remove {resource_type} {resource_id}: {remove_result.stderr.strip() or remove_result.stdout.strip() or 'unknown docker error'}"
                )

    if failures:
        raise RuntimeError("; ".join(failures))
