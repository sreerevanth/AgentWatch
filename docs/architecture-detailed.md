# Detailed Architecture Internals

## Event Bus Architecture
The event bus distributes asynchronous task tracing payloads to multiple targets. It runs on a thread-safe registry with reader-writer locks.

```mermaid
sequenceDiagram
    participant Agent as Agent Framework
    participant Adapter as GenericAdapter
    participant Bus as Event Bus
    participant Queue as Task Queue

    Agent->>Adapter: Execute Action
    Adapter->>Bus: publish_sync(Event)
    Bus->>Queue: Enqueue Trace
```

## Database Schema and Persistence
Database interactions map active telemetry via SQLAlchemy. Sessions are serialized as `AgentSession` models.
