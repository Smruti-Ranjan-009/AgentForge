from __future__ import annotations

import logging
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from agentforge.config import list_task_specs, load_task_spec
from agentforge.docker_utils import cleanup_agentforge_resources, find_active_task_container
from agentforge.grader import grade_task
from agentforge.reporter import write_report
from agentforge.runner import TaskRunner
from agentforge.validator import validate_all_tasks, validate_task

console = Console()
app = typer.Typer(help="AgentForge: Docker-based benchmark and evaluation platform for debugging tasks.")


def _configure_logging(verbose: bool) -> None:
    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO, format="%(levelname)s: %(message)s")


@app.callback()
def main(verbose: bool = typer.Option(False, "--verbose", help="Enable debug logging and stack traces.")) -> None:
    _configure_logging(verbose)


@app.command("list")
def list_tasks() -> None:
    tasks = list_task_specs()
    table = Table(title="Available AgentForge tasks")
    table.add_column("Task ID", overflow="fold")
    table.add_column("Title", overflow="fold")
    table.add_column("Category")
    table.add_column("Difficulty")
    table.add_column("Validation")
    for task in tasks:
        table.add_row(task.id, task.title, task.category, task.difficulty, "ready")
    console.print(table)


@app.command("inspect")
def inspect_task(task_id: str) -> None:
    spec = load_task_spec(task_id)
    task_path = Path(__file__).resolve().parent.parent / "tasks" / task_id
    panel = Panel.fit(
        f"ID: {spec.id}\nTitle: {spec.title}\nDifficulty: {spec.difficulty}\nCategory: {spec.category}\nTimeout: {spec.timeout_seconds}s\n\nDescription:\n{spec.description}\n\nInstruction: {task_path / 'instruction.md'}\nTests: {task_path / 'tests' / 'test.sh'}\nSolution: {task_path / 'solution' / 'solve.sh'}",
        title="Task metadata",
    )
    console.print(panel)


@app.command("validate")
def validate_command(task_id: str) -> None:
    console.print("AgentForge Task Validator\n────────────────────────────────")
    try:
        report = validate_task(task_id)
        for step in report.steps:
            mark = "✓" if step.success else "✗"
            console.print(f"{mark} {step.name}: {step.detail}")
        console.print(f"\n{report.message}")
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Validation failed: {exc}[/red]")
        raise typer.Exit(code=1)


@app.command("run")
def run_task(task_id: str) -> None:
    runner = TaskRunner(task_id)
    try:
        runner.run_task(interactive=True)
    except KeyboardInterrupt:
        console.print("[yellow]Task session ended.[/yellow]")
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Failed to start task: {exc}[/red]")
        raise typer.Exit(code=1)


@app.command("grade")
def grade_task_command(task_id: str) -> None:
    try:
        if find_active_task_container(task_id) is None:
            raise ValueError(f"No active environment found for {task_id}. Run `agentforge run {task_id}` first.")
        result = grade_task(task_id, container_name=find_active_task_container(task_id))
        console.print("Task Evaluation")
        console.print("────────────────────────────")
        console.print(f"Task: {task_id}")
        console.print(f"Tests passed:       {result.tests_passed} / {result.tests_total}")
        console.print(f"Task completed:     {'YES' if result.success else 'NO'}")
        console.print(f"Duration:           {result.duration_seconds} sec")
        console.print(f"Exit code:          {result.exit_code}")
        if result.stderr:
            console.print(f"\n[red]{result.stderr}[/red]")
        if not result.success:
            raise typer.Exit(code=1)
    except typer.Exit:
        raise
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Evaluation failed: {exc}[/red]")
        raise typer.Exit(code=1)


@app.command("solve")
def solve_task(task_id: str) -> None:
    try:
        runner = TaskRunner(task_id)
        result = runner.solve()
        if result.stdout:
            console.print(result.stdout)
        if result.stderr:
            console.print(f"[yellow]{result.stderr}[/yellow]")
        if result.returncode != 0:
            raise typer.Exit(code=result.returncode)
        console.print(f"[green]Reference solution executed for {task_id}[/green]")
    except typer.Exit:
        raise
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Solution failed: {exc}[/red]")
        raise typer.Exit(code=1)


@app.command("report")
def report_task(task_id: str) -> None:
    try:
        container_name = find_active_task_container(task_id)
        if container_name is None:
            raise ValueError(f"No active environment found for {task_id}. Run `agentforge run {task_id}` first.")
        result = grade_task(task_id, container_name=container_name)
        json_path, md_path = write_report(task_id, result, extra={"task": task_id, "category": "benchmark"})
        console.print(f"Report written to {json_path}")
        console.print(f"Markdown report written to {md_path}")
        if not result.success:
            raise typer.Exit(code=1)
    except typer.Exit:
        raise
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Failed to generate report: {exc}[/red]")
        raise typer.Exit(code=1)


@app.command("cleanup")
def cleanup_command() -> None:
    try:
        cleanup_agentforge_resources()
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Cleanup failed: {exc}[/red]")
        raise typer.Exit(code=1)
    console.print("[green]AgentForge resources cleaned up.[/green]")


@app.command("validate-all")
def validate_all() -> None:
    results = validate_all_tasks()
    table = Table(title="Task validation summary")
    table.add_column("Task")
    table.add_column("Status")
    table.add_column("Message")
    passed = 0
    for task_id in sorted(results):
        report = results[task_id]
        status = "PASS" if report.valid else "FAIL"
        if report.valid:
            passed += 1
        table.add_row(task_id, status, report.message)
    console.print(table)
    console.print(f"{passed}/{len(results)} tasks valid.")
    if passed != len(results):
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
