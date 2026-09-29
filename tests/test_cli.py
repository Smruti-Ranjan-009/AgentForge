from typer.testing import CliRunner

from agentforge.cli import app

runner = CliRunner()


def test_cli_list():
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "docker-network" in result.stdout.lower()


def test_cli_inspect():
    result = runner.invoke(app, ["inspect", "docker-network-debug"])
    assert result.exit_code == 0
    assert "Docker Network Debugging" in result.stdout


def test_cli_validate():
    result = runner.invoke(app, ["validate", "docker-network-debug"])
    assert result.exit_code == 0
    assert "Task valid" in result.stdout
