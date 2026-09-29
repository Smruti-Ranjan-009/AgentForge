import pytest

from agentforge.validator import validate_task


@pytest.mark.integration
def test_validate_docker_network_debug_docker_integration():
    report = validate_task("docker-network-debug")
    assert report.valid is True
    assert any(step.name == "broken state confirmed" for step in report.steps)
    assert any(step.name == "post-solution tests passed" for step in report.steps)
