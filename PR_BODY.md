## Summary
Resolves issue #397 (OBS-008). 
Implements Enterprise Telemetry allowing AgentWatch reasoning traces to be natively exported as OpenTelemetry span hierarchies. To prevent CPU starvation inside the event loop, this architecture delegates trace serialization inside the critical \TraceCollector\ lock while moving the actual OTLP export call outside the lock. Spans are batched and dispatched using the OpenTelemetry batching/export pipeline. Telemetry export is best-effort and does not imply delivery guarantees.

## Changes
- \export_reasoning_trace\: Added logic capable of parsing agent reasoning traces, preserving native parent-child Context links.
- \TraceCollector\ trigger: Intercepts \SESSION_END\ and \AGENT_ERROR\ terminal events to trigger OTel exports asynchronously.
- \Trace.is_exported\: Introduced explicit state to \Trace\ schemas to prevent duplicate export attempts, safely persisting to/from JSON storage buffers.
- \grafana/dashboards/agentwatch.json\: Provided a robust starter template for Enterprise metrics monitoring.
- Real tests: Configured rigorous unit coverage against actual \TracerProvider\ mocks by installing the OTel SDK into the \dev\ dependency group, avoiding falsely green skipped tests.

## Validation
- Full \pytest\ executed successfully across 584 integration boundaries.
- Disabled path verified: the exporter acts as a no-op when disabled, returning safely and omitting performance overhead.
- Compatibility checked: \load_from_disk()\ dynamically handles missing keys for legacy JSON checkpoints safely.
- Dashboard import tested and visually confirmed.

## Risks
- Rapid Application Crashes: An abrupt system \SIGKILL\ after a terminal event could kill the OpenTelemetry batching/export pipeline before network delivery resolves.
- Export is strictly best-effort.

## Rollback
- Disable via config: Simply omit OTel variables or the \[otel]\ extras group to bypass logic automatically.
- Revert safely: Standard Git revert of this PR cleanly removes the hook and dashboard without breaking existing API mechanics.

## Dashboard
A Grafana template for AgentWatch performance, duration, blocked events, and token consumption by framework is included natively at \grafana/dashboards/agentwatch.json\.
