"""Tests for the telemetry enhancements (buffering, idempotency, legacy config)."""

from __future__ import annotations

from unittest.mock import MagicMock

from agentwatch.telemetry.otel import TelemetryConfig, TelemetryProvider


def test_telemetry_config_backward_compatibility():
    # Test that both new and legacy parameters work
    config = TelemetryConfig(
        endpoint="http://legacy:4317", insecure=True, headers={"x-test": "val"}
    )
    assert config.otlp_endpoint == "http://legacy:4317"
    assert config.endpoint == "http://legacy:4317"
    assert config.insecure is True
    assert config.headers == {"x-test": "val"}


def test_telemetry_provider_buffering():
    provider = TelemetryProvider()
    mock_span = MagicMock()
    mock_span.name = "test-span"

    # Export before initialization should buffer
    provider.export(mock_span)
    assert len(provider._buffer) == 1
    assert provider._buffer[0] == mock_span


def test_telemetry_provider_buffer_overflow():
    provider = TelemetryProvider()
    provider._max_buffer_size = 5

    spans = []
    for i in range(10):
        s = MagicMock()
        s.name = f"span-{i}"
        spans.append(s)
        provider.export(s)

    assert len(provider._buffer) == 5
    # Should contain the LAST 5 spans (dropped oldest)
    assert provider._buffer[0].name == "span-5"
    assert provider._buffer[-1].name == "span-9"


def test_telemetry_initialization_idempotency():
    provider = TelemetryProvider()
    provider.initialize()
    assert provider._initialized is True

    # Second call should not raise or re-initialize
    provider.initialize()
    assert provider._initialized is True


def test_telemetry_flush_on_initialize():
    provider = TelemetryProvider()
    mock_span = MagicMock()
    mock_span.name = "flush-me"
    provider.export(mock_span)

    # Mock exporter to verify flush
    mock_exporter = MagicMock()
    provider._exporter = mock_exporter

    provider.initialize()
    assert len(provider._buffer) == 0
    # exporter.export should have been called (via provider.export in flush)
    assert mock_exporter.export.called


def test_telemetry_record_methods():
    provider = TelemetryProvider()
    provider.initialize()

    # These should not raise even if OTel is not fully active
    provider.record_event("framework", "event")
    provider.record_blocked("framework", "high")
    provider.record_tokens(100, "framework")
    provider.record_session_duration(1.5, "framework", "success")


def test_export_retries_until_success():
    provider = TelemetryProvider()

    exporter = MagicMock()
    exporter.export.side_effect = [
        Exception("network"),
        Exception("network"),
        None,
    ]

    provider._initialized = True
    provider._exporter = exporter

    span = MagicMock()
    provider.export(span)

    assert exporter.export.call_count == 3


def test_export_gives_up_after_max_retries():
    provider = TelemetryProvider()

    exporter = MagicMock()
    exporter.export.side_effect = Exception("network")

    provider._initialized = True
    provider._exporter = exporter

    span = MagicMock()
    provider.export(span)

    assert exporter.export.call_count == 3
