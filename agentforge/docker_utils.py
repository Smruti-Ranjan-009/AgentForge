from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from uuid import uuid4

from agentforge.exceptions import BuildError, DockerUnavailableError

NETWORKED_TASK_ID = "docker-network-debug"


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
    if task_id == NETWORKED_TASK_ID:
        docker_cmd[-2:-2] = ["--filter", "label=agentforge.component=client"]
    result = run_command(docker_cmd, capture_output=True, check=False)
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def find_active_task_container(task_id: str) -> str | None:
    active = _list_task_containers(task_id)
    return active[0] if active else None


def _ensure_networked_task_resources(task_id: str, image_name: str) -> str:
    network_name = f"agentforge-{task_id}-network"
    network_list = run_command(
        [
            "docker",
            "network",
            "ls",
            "-q",
            "--filter",
            "label=agentforge.managed=true",
            "--filter",
            f"label=agentforge.task={task_id}",
        ],
        capture_output=True,
        check=False,
    )
    if network_list.returncode != 0:
        raise RuntimeError(f"Failed to list Docker networks: {network_list.stderr.strip() or network_list.stdout.strip()}")

    if network_list.stdout.strip():
        network_name = network_list.stdout.splitlines()[0].strip()
    else:
        network_create = run_command(
            [
                "docker",
                "network",
                "create",
                "--label",
                "agentforge.managed=true",
                "--label",
                f"agentforge.task={task_id}",
                network_name,
            ],
            capture_output=True,
            check=False,
        )
        if network_create.returncode != 0:
            raise RuntimeError(f"Failed to create network {network_name}: {network_create.stderr.strip() or network_create.stdout.strip()}")

    backend_name = f"agentforge-{task_id}-backend"
    inspect = run_command(["docker", "inspect", "--format", "{{.State.Running}}", backend_name], capture_output=True, check=False)
    if inspect.returncode == 0 and inspect.stdout.strip().lower() == "true":
        backend_running = True
    else:
        if inspect.returncode == 0:
            remove = run_command(["docker", "rm", "-f", backend_name], capture_output=True, check=False)
            if remove.returncode != 0:
                raise RuntimeError(f"Failed to remove stopped backend container {backend_name}: {remove.stderr.strip() or remove.stdout.strip()}")
        start = run_command(
            [
                "docker",
                "run",
                "-d",
                "--name",
                backend_name,
                "--network",
                network_name,
                "--network-alias",
                "backend",
                "--label",
                "agentforge.managed=true",
                "--label",
                f"agentforge.task={task_id}",
                "--label",
                "agentforge.component=backend",
                image_name,
                "python",
                "/workspace/backend.py",
            ],
            capture_output=True,
            check=False,
        )
        if start.returncode != 0:
            raise RuntimeError(f"Failed to start backend container {backend_name}: {start.stderr.strip() or start.stdout.strip()}")
        backend_running = True

    if backend_running:
        for _ in range(40):
            ready = run_command(
                [
                    "docker",
                    "exec",
                    backend_name,
                    "python",
                    "-c",
                    "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000', timeout=1).read()",
                ],
                capture_output=True,
                timeout=3,
                check=False,
            )
            if ready.returncode == 0:
                break
            time.sleep(0.25)
        else:
            raise RuntimeError(f"Backend container {backend_name} did not become healthy: {ready.stderr.strip() or ready.stdout.strip()}")

    return network_name


def start_task_container(task_id: str, image_name: str) -> str:
    ensure_docker_available()
    if task_id == NETWORKED_TASK_ID:
        network_name = _ensure_networked_task_resources(task_id, image_name)
        active = _list_task_containers(task_id)
        if active:
            return active[0]
        existing = _list_task_containers(task_id, include_stopped=True)
        for container_name in existing:
            remove = run_command(["docker", "rm", "-f", container_name], capture_output=True, check=False)
            if remove.returncode != 0:
                raise RuntimeError(f"Failed to remove client container {container_name}: {remove.stderr.strip() or remove.stdout.strip()}")

        container_name = f"agentforge-{task_id}"
        start = run_command(
            [
                "docker",
                "run",
                "-d",
                "--name",
                container_name,
                "--network",
                network_name,
                "--label",
                "agentforge.managed=true",
                "--label",
                f"agentforge.task={task_id}",
                "--label",
                "agentforge.component=client",
                image_name,
                "bash",
                "-lc",
                "while true; do sleep 60; done",
            ],
            capture_output=True,
            check=False,
        )
        if start.returncode != 0:
            raise RuntimeError(f"Failed to start client container {container_name}: {start.stderr.strip() or start.stdout.strip()}")
        return container_name

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
