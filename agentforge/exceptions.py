class AgentForgeError(Exception):
    """Base error for AgentForge."""


class TaskNotFoundError(AgentForgeError):
    def __init__(self, task_id: str):
        super().__init__(f"Task '{task_id}' was not found.")


class TaskConfigError(AgentForgeError):
    def __init__(self, message: str):
        super().__init__(message)


class DockerUnavailableError(AgentForgeError):
    def __init__(self, message: str = "Docker is unavailable or not running."):
        super().__init__(message)


class BuildError(AgentForgeError):
    def __init__(self, message: str):
        super().__init__(message)


class EvaluationError(AgentForgeError):
    def __init__(self, message: str):
        super().__init__(message)


class TimeoutError(AgentForgeError):
    def __init__(self, message: str):
        super().__init__(message)
