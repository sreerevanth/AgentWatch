from unittest.mock import patch

import pytest

from agentwatch.infrastructure.config import RouterConfig
from agentwatch.infrastructure.router import ModelRouter


class DummyConfig(RouterConfig):
    def __init__(self, config_dict):
        self._config = config_dict

    def get_config(self):
        return self._config


@pytest.fixture
def mock_config():
    return DummyConfig(
        {
            "providers": {
                "primary": "gpt-4o",
                "fallback": ["claude-3-haiku-20240307", "gemini-1.5-flash"],
            }
        }
    )


@patch("tenacity.nap.sleep")
def test_provider_fallback(mock_sleep, mock_config):
    router = ModelRouter(mock_config)

    with patch("agentwatch.infrastructure.router.litellm.completion") as mock_completion:
        # First provider fails 3 times (due to tenacity retries), then second provider succeeds
        mock_completion.side_effect = [
            Exception("API error"),
            Exception("API error"),
            Exception("API error"),
            {"choices": [{"message": {"content": "hello"}}]},
        ]

        res = router.completion([{"role": "user", "content": "hi"}])
        assert res == {"choices": [{"message": {"content": "hello"}}]}

        metrics = router.get_metrics()
        assert metrics["fallback_counts"] == 1
        assert metrics["providers"]["gpt-4o"]["failures"] == 1
        assert metrics["providers"]["claude-3-haiku-20240307"]["failures"] == 0


@patch("tenacity.nap.sleep")
def test_circuit_breaker_transitions(mock_sleep, mock_config):
    router = ModelRouter(mock_config)

    with patch("agentwatch.infrastructure.router.litellm.completion") as mock_completion:
        mock_completion.side_effect = Exception("API error")

        import contextlib

        for _ in range(5):
            with contextlib.suppress(Exception):
                router.completion([{"role": "user", "content": "hi"}])

        metrics = router.get_metrics()
        assert metrics["providers"]["gpt-4o"]["state"] == "OPEN"
