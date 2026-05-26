"""
OBS-008 — Grafana / OTEL Export.

Pushes spans to any OpenTelemetry-compatible backend.
When the optional `otel` extra is not installed, falls back to a no-op
exporter that buffers spans in memory so the rest of the pipeline keeps
working — and tests can still verify behavior.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from agentwatch.core.schema import AgentEvent
from agentwatch.tracing.spans import Span, event_to_span

logger = logging.getLogger(__name__)


@dataclass
class OTELConfig:
    endpoint: str = "http://localhost:4317"
    service_name: str = "agentwatch"
    insecure: bool = True
    headers: dict[str, str] = field(default_factory=dict)


class OTELExporter:
    """
    Export AgentWatch spans via OpenTelemetry OTLP.
    If the OTEL libraries are unavailable, becomes an in-memory buffer.
    """

    def __init__(self, config: OTELConfig | None = None):
        self.config = config or OTELConfig()
        self._buffer: list[Span] = []
        self._tracer = None
        self._initialized = False
        self._fallback = False
        self._init()

    def _init(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        try:
            from opentelemetry import trace  # noqa: PLC0415
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (  # noqa: PLC0415
                OTLPSpanExporter,
            )
            from opentelemetry.sdk.resources import Resource  # noqa: PLC0415
            from opentelemetry.sdk.trace import TracerProvider  # noqa: PLC0415
            from opentelemetry.sdk.trace.export import BatchSpanProcessor  # noqa: PLC0415

            resource = Resource.create({"service.name": self.config.service_name})
            provider = TracerProvider(resource=resource)
            exporter = OTLPSpanExporter(
                endpoint=self.config.endpoint,
                insecure=self.config.insecure,
                headers=self.config.headers or None,
            )
            provider.add_span_processor(BatchSpanProcessor(exporter))
            trace.set_tracer_provider(provider)
            self._tracer = trace.get_tracer("agentwatch")
            self._fallback = False
            logger.info("OTEL exporter initialized → %s", self.config.endpoint)
        except Exception as exc:  # noqa: BLE001
            logger.info("OTEL deps unavailable, using in-memory fallback: %s", exc)
            self._fallback = True

    def export(self, span: Span) -> None:
        if self._fallback or self._tracer is None:
            self._buffer.append(span)
            return
        try:
            with self._tracer.start_as_current_span(span.name) as otel_span:
                for k, v in span.attributes.items():
                    otel_span.set_attribute(k, str(v))
                if span.token_count:
                    otel_span.set_attribute("llm.tokens", span.token_count)
                if span.error:
                    otel_span.record_exception(Exception(span.error))
        except Exception as exc:  # noqa: BLE001
            logger.warning("OTEL export failed: %s", exc)
            self._buffer.append(span)

    def export_event(self, event: AgentEvent) -> None:
        self.export(event_to_span(event))

    @property
    def buffered(self) -> list[Span]:
        return list(self._buffer)

    def grafana_dashboard_template(self) -> dict[str, Any]:
        """Return a minimal Grafana dashboard JSON for AgentWatch metrics."""
        return {
            "title": "AgentWatch — Reasoning Trace",
            "uid": "agentwatch-main",
            "tags": ["agentwatch", "ai-agents"],
            "timezone": "browser",
            "panels": [
                {
                    "id": 1,
                    "title": "Tool calls per minute",
                    "type": "graph",
                    "targets": [
                        {"expr": "rate(agentwatch_tool_calls_total[1m])"}
                    ],
                },
                {
                    "id": 2,
                    "title": "Confidence (p50 / p95)",
                    "type": "graph",
                    "targets": [
                        {
                            "expr": "histogram_quantile(0.5, "
                            "rate(agentwatch_confidence_bucket[5m]))"
                        },
                        {
                            "expr": "histogram_quantile(0.95, "
                            "rate(agentwatch_confidence_bucket[5m]))"
                        },
                    ],
                },
                {
                    "id": 3,
                    "title": "Blocked actions",
                    "type": "stat",
                    "targets": [{"expr": "agentwatch_blocks_total"}],
                },
            ],
        }


__all__ = ["OTELExporter", "OTELConfig"]
