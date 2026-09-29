# Contributing to AgentForge

Thanks for helping improve the benchmark framework.

## Project layout

```text
agentforge/
├── agentforge/
├── tasks/
├── tests/
├── reports/
├── scripts/
├── README.md
├── CONTRIBUTING.md
├── LICENSE
├── pyproject.toml
└── .gitignore
```

## Creating a new benchmark

Create a task directory like this:

```text
tasks/<task-id>/
├── task.yaml
├── instruction.md
├── environment/
│   └── Dockerfile
├── solution/
│   └── solve.sh
├── tests/
│   └── test.sh
└── ...
```

### Requirements

- `task.yaml` must validate against the AgentForge schema
- the environment must fail deterministically before the fix
- the reference solution must produce a passing result
- tests must assert observable behavior rather than static file contents
- the task must be reproducible locally and must not call external services

### Quality criteria

- keep the challenge realistic and engineer-facing
- avoid trivial grep-based checks
- ensure the broken setup fails consistently
- ensure the fix requires genuine debugging work
- keep dependencies pinned when external packages are used
- prefer local shell/Python-based checks over cloud-dependent tooling

## Local development

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .[dev]
python -m pytest
```

## Validation flow

Before submitting a change, run:

```powershell
agentforge validate <task-id>
python -m pytest
```

Large framework or Docker changes should also be checked with:

```powershell
agentforge list
agentforge cleanup
```

## Coding expectations

- prefer small, focused functions
- use `pathlib` for filesystem operations
- keep CLI output clean and professional
- handle expected failures gracefully with custom exceptions
- test actual behavior instead of mock-only expectations
