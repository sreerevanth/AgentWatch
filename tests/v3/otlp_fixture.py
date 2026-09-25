"""Shared OTLP/JSON request used by several v3 tests."""

OTLP = {
    "resourceSpans": [{
        "resource": {"attributes": [{"key": "service.name", "value": {"stringValue": "rag-api"}}]},
        "scopeSpans": [{"scope": {"name": "test"}, "spans": [
            {"traceId": "a" * 32, "spanId": "1" * 16, "name": "POST /ask", "kind": 2,
             "startTimeUnixNano": "1700000000000000000", "endTimeUnixNano": "1700000002000000000",
             "attributes": [{"key": "http.request.method", "value": {"stringValue": "POST"}}], "status": {}},
            {"traceId": "a" * 32, "spanId": "2" * 16, "parentSpanId": "1" * 16, "name": "chat gpt-4o", "kind": 3,
             "startTimeUnixNano": "1700000000500000000", "endTimeUnixNano": "1700000001500000000",
             "attributes": [
                 {"key": "gen_ai.operation.name", "value": {"stringValue": "chat"}},
                 {"key": "gen_ai.system", "value": {"stringValue": "openai"}},
                 {"key": "gen_ai.request.model", "value": {"stringValue": "gpt-4o"}},
                 {"key": "gen_ai.usage.input_tokens", "value": {"intValue": "120"}},
                 {"key": "gen_ai.usage.output_tokens", "value": {"intValue": "30"}}],
             "status": {"code": 2, "message": "rate limited"}},
            {"traceId": "a" * 32, "spanId": "3" * 16, "parentSpanId": "1" * 16, "name": "SELECT docs", "kind": 3,
             "startTimeUnixNano": "1700000000100000000", "endTimeUnixNano": "1700000000200000000",
             "attributes": [{"key": "db.system", "value": {"stringValue": "postgresql"}}, {"key": "db.operation", "value": {"stringValue": "SELECT"}}],
             "links": [{"traceId": "a" * 32, "spanId": "2" * 16}]},
        ]}],
    }],
}
