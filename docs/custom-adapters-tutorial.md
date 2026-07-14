# Custom Adapters Tutorial

## Implementation Steps
To build a custom wrapper for framework targets:

### 1. Intercepting Tool Loops
Create wrappers using execution decorators:
```python
def custom_execution_wrapper(func):
    def wrapper(*args, **kwargs):
        # 1. Evaluate safety gates
        # 2. Publish start event
        result = func(*args, **kwargs)
        # 3. Publish completion event
        return result
    return wrapper
```

### 2. Publishing Custom Telemetry
Publish telemetry payloads using `get_event_bus().publish_sync(event)`.
