import json
from types import SimpleNamespace

from agentforge.grader import grade_task, parse_json_payload


def test_parse_json_payload():
    payload = parse_json_payload('prefix {"passed": 2, "total": 2, "success": true} suffix')
    assert payload is not None
    assert payload["success"] is True


def test_grade_task_parses_json(mocker):
    mocker.patch(
        "subprocess.run",
        return_value=SimpleNamespace(returncode=0, stdout='{"passed": 3, "total": 3, "success": true}', stderr=""),
    )
    result = grade_task("docker-network-debug", image_name="agentforge-docker-network-debug:test")
    assert result.success is True
    assert result.tests_total == 3
    assert result.tests_passed == 3
