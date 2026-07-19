# AgentWatch v0.3.0 Release Notes

## The Brutalist Purge

Version 0.3.0 of AgentWatch marks a significant turning point in the project's evolution. Over the past several months, the codebase accreted speculative features, theoretical models, and complex architectures that strayed from the project's core mission. We had orchestration layers that weren't orchestrating, reasoning models that were too abstract to be practical, and a sprawling, complex memory system.

With the v0.3.0 release, we have enacted a "Brutalist Purge." Guided by a strict adherence to YAGNI (You Aren't Gonna Need It) and the Unix philosophy of doing one thing well, we have stripped the system down to its absolute essentials.

### New Scope and Core Focus
AgentWatch is returning to its roots as a robust, highly-performant **Observability, Safety, and Reliability Layer for AI Agents**. 

The scope is now tightly defined around:
1. **Telemetry & Tracing:** Fast, resilient tracking of agent reasoning, tool usage, and lifecycle events.
2. **Safety & Policy:** Core circuit-breaking and action gating based on predefined policies.
3. **Core API:** A lean, dependable API and dashboard to monitor agent behavior.

### What We Removed (The Bloat)
- **Orchestration Layer:** Eliminated theoretical multi-agent routing. Your agents should dictate their own orchestration; AgentWatch will monitor them.
- **Complex Memory Engine:** Removed the over-engineered contextual graph storage.
- **Reasoning Auditor:** Stripped out the logic fingerprinting and theoretical auditor models that complicated the dependency tree without delivering immediate value. The `benchmarks/run_eval.py` benchmark suite is deprecated.
- **Governance Modules:** Removed EU AI Act speculative features.
- **Cost Tracking Overhead:** Cut premature cost-tracking optimizations that bogged down processing. The `agentwatch cost report` CLI command is deprecated, and semantic caching has been removed from adapters.

### Why This Matters
By deleting over 11,000 lines of non-essential code, we have achieved:
- **Massively Improved Performance:** Fewer abstractions mean a faster event loop and reduced overhead on your systems.
- **Unbreakable CI/CD:** A pruned, stable test suite that guarantees the reliability of the core API.
- **Reduced Surface Area:** A simpler system is a more secure system.

AgentWatch 0.3.0 is lean, robust, and ready for production workloads.
