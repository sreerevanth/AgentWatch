import timeit
import json
import asyncio
from agentwatch.core.watcher import watch, GenericAdapter
from agentwatch.core.safety import SafetyEngine
from agentwatch.core.event_bus import EventBus
from agentwatch.core.schema import AgentEvent, EventType

# Shared benchmark objects for full_api_round_trip
_bench_bus = EventBus()
_bench_event = AgentEvent(
    session_id="bench",
    agent_id="bench",
    event_type=EventType.TOOL_CALL,
)
_bench_loop = asyncio.new_event_loop()

# Simple dummy agent function for baseline
def dummy_agent_sync():
    # Simulate minimal work with a tiny CPU loop to avoid zero‑time measurements
    total = 0
    for i in range(100):
        total += i
    return "ok"

# Instrumented call without safety engine
watched_no_safety = watch(dummy_agent_sync)  # pre‑instrumented call without safety

def dummy_agent_watch_no_safety():
    return watched_no_safety()

# Instrumented call with safety engine
safety_engine = SafetyEngine()

attached_with_safety = GenericAdapter(dummy_agent_sync, safety_engine=safety_engine).attach()  # pre‑instrumented call with safety

def dummy_agent_watch_with_safety():
    return attached_with_safety()

# Full API round‑trip (starts the FastAPI server and posts an event)
# For the benchmark we mock the server call to avoid external services.
def full_api_round_trip():
    # Simulate a full API round‑trip by invoking the async EventBus.publish
    # with a minimal, correctly‑typed AgentEvent. This exercises the async
    # dispatch path without starting the FastAPI server.
    # We use the pre-initialized _bench_loop and _bench_bus to avoid setup overhead.
    _bench_loop.run_until_complete(_bench_bus.publish(_bench_event))


def run_benchmarks():
    # Number of individual calls to time per batch. Using a larger repeat count
    # yields many per‑call samples so p95/p99 are meaningful.
    # Number of individual benchmark samples (per‑call timings)
    # Using a larger repeat count gives a robust distribution for p95/p99.
    sample_count = 1000
    results = {}
    raw_means = {}
    for name, func in [
        ("baseline", dummy_agent_sync),
        ("watch_no_safety", dummy_agent_watch_no_safety),
        ("watch_with_safety", dummy_agent_watch_with_safety),
        ("full_api", full_api_round_trip),
    ]:
        # Time the function `sample_count` times, recording each individual call duration
        timer = timeit.Timer(func)
        raw = [timer.timeit(number=1) for _ in range(sample_count)]
        # compute statistics over the per‑call samples
        mean = sum(raw) / len(raw)
        p95 = sorted(raw)[int(0.95 * len(raw))]
        p99 = sorted(raw)[int(0.99 * len(raw))]
        
        mean_ms = mean * 1000
        raw_means[name] = mean_ms
        results[name] = {
            "mean_ms": round(mean_ms, 3),
            "p95_ms": round(p95 * 1000, 3),
            "p99_ms": round(p99 * 1000, 3),
        }
    # calculate overhead percentages vs baseline
    base_raw = raw_means["baseline"]
    for name, data in results.items():
        if name != "baseline":
            data["overhead_%"] = round(((raw_means[name] - base_raw) / base_raw) * 100, 2)
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    run_benchmarks()
