from unittest.mock import patch

from typer.testing import CliRunner

from agentwatch.cli.main import app

runner = CliRunner()


@patch("agentwatch.cli.verify_env.verify_environment")
def test_check_env_calls_verify_environment(mock_verify_environment):
    result = runner.invoke(app, ["check-env"])

    assert result.exit_code == 0
    mock_verify_environment.assert_called_once()
