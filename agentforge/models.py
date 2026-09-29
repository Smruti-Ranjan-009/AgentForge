from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


class TaskSpec(BaseModel):
    id: str
    title: str
    difficulty: str
    category: str
    description: str
    timeout_seconds: int = Field(default=600, ge=1)
    environment: dict[str, Any]
    tests: dict[str, str]
    solution: dict[str, str]
    tags: list[str] = Field(default_factory=list)

    @field_validator("difficulty")
    @classmethod
    def validate_difficulty(cls, value: str) -> str:
        allowed = {"easy", "medium", "hard"}
        if value.lower() not in allowed:
            raise ValueError(f"difficulty must be one of {sorted(allowed)}")
        return value.lower()

    @field_validator("category")
    @classmethod
    def validate_category(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("category is required")
        return value.strip()

    @property
    def dockerfile_path(self) -> str:
        return str(self.environment.get("dockerfile", "environment/Dockerfile"))

    @property
    def test_command(self) -> str:
        return self.tests.get("command", "bash tests/test.sh")

    @property
    def solution_command(self) -> str:
        return self.solution.get("command", "bash solution/solve.sh")


class EvaluationResult(BaseModel):
    task_id: str
    success: bool
    tests_passed: int
    tests_total: int
    duration_seconds: float
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    error_category: str = "SUCCESS"
    notes: str = ""


class ValidationStep(BaseModel):
    name: str
    success: bool
    detail: str = ""


class ValidationReport(BaseModel):
    task_id: str
    valid: bool
    steps: list[ValidationStep] = Field(default_factory=list)
    message: str = ""
