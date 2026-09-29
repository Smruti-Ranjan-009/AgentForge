from __future__ import annotations

import subprocess
from pathlib import Path

from agentforge.config import load_task_spec
from agentforge.docker_utils import build_image, ensure_docker_available, find_active_task_container, run_command, start_task_container
from agentforge.exceptions import EvaluationError


class TaskRunner:
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.spec = load_task_spec(task_id)
        self.task_path = Path(__file__).resolve().parent.parent / "tasks" / task_id

    def build(self, *, verbose: bool = False) -> str:
        return build_image(self.task_path, self.task_id, verbose=verbose)

    def execute(self, command: str, *, interactive: bool = False, timeout: int | None = None) -> subprocess.CompletedProcess[str]:
        container_name = find_active_task_container(self.task_id)
        if container_name is None:
            image_name = self.build(verbose=False)
            container_name = start_task_container(self.task_id, image_name)
        return run_command(["docker", "exec", "-it" if interactive else "exec", container_name, "bash", "-lc", command], capture_output=not interactive, interactive=interactive, timeout=timeout)

    def run_task(self, *, interactive: bool = False) -> None:
        ensure_docker_available()
        image_name = self.build(verbose=False)
        container_name = find_active_task_container(self.task_id)
        if container_name is None:
            container_name = start_task_container(self.task_id, image_name)
            print(f"Starting task: {self.task_id}\n")
            print("Environment:\n")
            print(f"Container: {container_name}\n")
            print(f"Image: {image_name}\n")
            print("Task:")
            print(self.spec.description)
        else:
            print(f"Reusing existing task environment: {container_name}\n")
        print("\nOpening shell...\n")
        run_command(["docker", "exec", "-it", container_name, "bash"], interactive=True)

    def solve(self, *, verbose: bool = False) -> subprocess.CompletedProcess[str]:
        image_name = self.build(verbose=verbose)
        command = self.spec.solution_command
        return run_command(
            [
                "docker",
                "run",
                "--rm",
                "--label",
                "agentforge.managed=true",
                "--label",
                f"agentforge.task={self.task_id}",
                "--entrypoint",
                "bash",
                image_name,
                "-lc",
                command,
            ],
            capture_output=True,
            timeout=self.spec.timeout_seconds,
        )

    def grade(self, *, command: str | None = None, timeout: int | None = None) -> subprocess.CompletedProcess[str]:
        container_name = find_active_task_container(self.task_id)
        if container_name is None:
            raise EvaluationError(f"No active environment found for {self.task_id}. Run `agentforge run {self.task_id}` first.")
        result = run_command(
            [
                "docker",
                "exec",
                container_name,
                "bash",
                "-lc",
                command or self.spec.test_command,
            ],
            capture_output=True,
            timeout=timeout or self.spec.timeout_seconds,
        )
        return result
