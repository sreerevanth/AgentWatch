import timeit
import json
from agentwatch.core.watcher import watch, GenericAdapter
from agentwatch.core.safety import SafetyEngine

# Simple dummy agent function for baseline
def dummy_agent_sync():
    # Simulate minimal work with a tiny CPU loop to avoid zero‑time measurements
    total = 0
    for i in range(100):
        total += i
    return "ok"

# Instrumented call without safety engine
def dummy_agent_watch_no_safety():
    watched = watch(dummy_agent_sync)  # watch without safety
    return watched()

# Instrumented call with safety engine
safety_engine = SafetyEngine()

def dummy_agent_watch_with_safety():
    # Use GenericAdapter directly because watch() does not expose a safety_engine argument.
    adapter = GenericAdapter(dummy_agent_sync, safety_engine=safety_engine)
    watched = adapter.attach()
    return watched()

# Full API round‑trip (starts the FastAPI server and posts an event)
# For the benchmark we mock the server call to avoid external services.
def full_api_round_trip():
    # The actual implementation uses the HTTP client inside AgentWatch;
    # here we simply invoke the event publishing path synchronously.
    from agentwatch.core.event_bus import EventBus
    bus = EventBus()
    # Publish a minimal event; the bus processes it synchronously.
    bus.publish({"type": "test", "payload": {"msg": "ping"}})


def run_benchmarks():
    repetitions = 1000
    results = {}
    for name, func in [
        ("baseline", dummy_agent_sync),
        ("watch_no_safety", dummy_agent_watch_no_safety),
        ("watch_with_safety", dummy_agent_watch_with_safety),
        ("full_api", full_api_round_trip),
    ]:
        timer = timeit.Timer(func)
        raw = timer.repeat(repeat=5, number=repetitions)
        # compute statistics
        mean = sum(raw) / len(raw) / repetitions
        p95 = sorted(raw)[int(0.95 * len(raw))] / repetitions
        p99 = sorted(raw)[int(0.99 * len(raw))] / repetitions
        results[name] = {
            "mean_ms": round(mean * 1000, 3),
            "p95_ms": round(p95 * 1000, 3),
            "p99_ms": round(p99 * 1000, 3),
        }
    # calculate overhead percentages vs baseline
    base = results["baseline"]["mean_ms"]
    for name, data in results.items():
        if name != "baseline":
            data["overhead_%"] = round(((data["mean_ms"] - base) / base) * 100, 2)
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    run_benchmarks()
