"""
AgentWatch Telemetry
OpenTelemetry integration for distributed tracing, metrics, and logging.
Exports spans to OTLP, Jaeger, or stdout.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any, Dict, Generator, Optional

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# OTel imports — graceful degradation if absent
# ─────────────────────────────────────────────
try:
    from opentelemetry import trace, metrics
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import (
        ConsoleMetricExporter,
        PeriodicExportingMetricReader,
    )
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.semconv.resource import ResourceAttributes

    _OTEL_AVAILABLE = True
except ImportError:
    _OTEL_AVAILABLE = False
    logger.debug("opentelemetry-sdk not installed — telemetry disabled")


class TelemetryConfig:
    def __init__(
        self,
        service_name: str = "agentwatch",
        service_version: str = "0.2.0",
        otlp_endpoint: Optional[str] = None,
        export_to_console: bool = False,
        enable_metrics: bool = True,
        endpoint: Optional[str] = None,  # Compatibility alias
    ):
        self.service_name = service_name
        self.service_version = service_version
        self.otlp_endpoint = endpoint or otlp_endpoint
        self.export_to_console = export_to_console
        self.enable_metrics = enable_metrics


# Compatibility aliases for OBS tests
OTELConfig = TelemetryConfig


class TelemetryProvider:
    """
    Wraps OpenTelemetry setup for AgentWatch.
    Falls back gracefully when OTel SDK is not installed.
    """

    def __init__(self, config: Optional[TelemetryConfig] = None):
        self._config = config or TelemetryConfig()
        self._tracer = None
        self._meter = None
        self._initialized = False
        self._buffer: list[Any] = []

        # Metric instruments (created after init)
        self._event_counter = None
        self._blocked_counter = None
        self._session_duration = None
        self._token_counter = None

    def export(self, span: Any) -> None:
        """Export a span to the configured backend (or buffer if failing)."""
        if not self._initialized:
            self._buffer.append(span)
            return
        # Real OTel export would happen here if SDK is available
        logger.debug("Exported span: %s", span.name)

    def grafana_dashboard_template(self) -> dict[str, Any]:
        """Return a basic Grafana dashboard template for AgentWatch."""
        return {
            "uid": "agentwatch-main",
            "title": "AgentWatch Observability",
            "panels": [
                {"title": "Confidence (p50 / p95)", "type": "timeseries"},
                {"title": "Risk Levels", "type": "piechart"},
                {"title": "Token Consumption", "type": "stat"},
            ],
        }

    def initialize(self) -> None:
        if not _OTEL_AVAILABLE:
            logger.info("OpenTelemetry not available — skipping telemetry init")
            return

        resource = Resource.create({
            ResourceAttributes.SERVICE_NAME: self._config.service_name,
            ResourceAttributes.SERVICE_VERSION: self._config.service_version,
        })

        # ── Tracing setup ────────────────────────────────────────────────
        tracer_provider = TracerProvider(resource=resource)

        if self._config.otlp_endpoint:
            try:
                from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
                otlp_exporter = OTLPSpanExporter(endpoint=self._config.otlp_endpoint)
                tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
                logger.info("OTLP span exporter configured: %s", self._config.otlp_endpoint)
            except ImportError:
                logger.warning("opentelemetry-exporter-otlp not installed")

        if self._config.export_to_console:
            tracer_provider.add_span_processor(
                BatchSpanProcessor(ConsoleSpanExporter())
            )

        trace.set_tracer_provider(tracer_provider)
        self._tracer = trace.get_tracer(
            self._config.service_name,
            self._config.service_version,
        )

        # ── Metrics setup ────────────────────────────────────────────────
        if self._config.enable_metrics:
            readers = []
            if self._config.otlp_endpoint:
                try:
                    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
                        OTLPMetricExporter,
                    )
                    metric_exporter = OTLPMetricExporter(endpoint=self._config.otlp_endpoint)
                    readers.append(PeriodicExportingMetricReader(metric_exporter))
                except ImportError:
                    pass

            if self._config.export_to_console:
                readers.append(
                    PeriodicExportingMetricReader(ConsoleMetricExporter(), export_interval_millis=60000)
                )

            meter_provider = MeterProvider(resource=resource, metric_readers=readers)
            metrics.set_meter_provider(meter_provider)
            self._meter = metrics.get_meter(self._config.service_name)
            self._create_instruments()

        self._initialized = True
        logger.info("Telemetry initialized (service=%s)", self._config.service_name)

    def _create_instruments(self) -> None:
        if not self._meter:
            return
        self._event_counter = self._meter.create_counter(
            "agentwatch.events.total",
            description="Total agent events processed",
        )
        self._blocked_counter = self._meter.create_counter(
            "agentwatch.safety.blocked_total",
            description="Total actions blocked by safety engine",
        )
        self._token_counter = self._meter.create_counter(
            "agentwatch.tokens.total",
            description="Total LLM tokens consumed",
        )
        self._session_duration = self._meter.create_histogram(
            "agentwatch.session.duration_seconds",
            description="Agent session duration in seconds",
        )

    @contextmanager
    def span(
        self,
        name: str,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> Generator:
        """Context manager to create a trace span."""
        if not self._tracer:
            yield None
            return

        with self._tracer.start_as_current_span(name) as span:
            if attributes:
                for k, v in attributes.items():
                    span.set_attribute(k, str(v))
            yield span

    def record_event(self, framework: str, event_type: str) -> None:
        if self._event_counter:
            self._event_counter.add(1, {"framework": framework, "event_type": event_type})

    def record_blocked(self, framework: str, risk_level: str) -> None:
        if self._blocked_counter:
            self._blocked_counter.add(1, {"framework": framework, "risk_level": risk_level})

    def record_tokens(self, count: int, framework: str) -> None:
        if self._token_counter:
            self._token_counter.add(count, {"framework": framework})

    def record_session_duration(self, duration_seconds: float, framework: str, status: str) -> None:
        if self._session_duration:
            self._session_duration.record(
                duration_seconds, {"framework": framework, "status": status}
            )


# Compatibility alias for OBS tests
OTELExporter = TelemetryProvider

# Singleton
_provider: Optional[TelemetryProvider] = None


def get_telemetry() -> TelemetryProvider:
    global _provider
    if _provider is None:
        _provider = TelemetryProvider()
    return _provider


def init_telemetry(config: TelemetryConfig) -> TelemetryProvider:
    global _provider
    _provider = TelemetryProvider(config)
    _provider.initialize()
    return _provider
