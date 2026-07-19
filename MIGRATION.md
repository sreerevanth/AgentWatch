# Migration Guide for AgentWatch 0.4.0 (Brutalist Purge)

Version 0.4.0 marks a significant pivot in AgentWatch, focusing ruthlessly on our core value proposition: Safety, Observability, and Reliability for AI agents. We have purged speculative, "academic", and non-core features to enforce YAGNI (You Aren't Gonna Need It).

If you are upgrading from 0.3.x, please review the breaking changes below.

## Removed Features & APIs

The following modules and their associated APIs have been completely removed:

1. **Orchestration Layer (`agentwatch.orchestration`)**
   - **Why:** AgentWatch is an observability and safety layer, not an agent orchestration framework. Rely on specialized frameworks (like LangChain, LlamaIndex, or raw LLM calls) for orchestration.
   - **Action required:** Remove any imports from `agentwatch.orchestration`. Move your orchestration logic to your preferred framework.

2. **Memory Modules (`agentwatch.memory`)**
   - **Why:** Complex vector and graph memory management is outside the scope of AgentWatch's core mission.
   - **Action required:** Migrate your agent's memory systems to purpose-built databases or libraries (e.g., Pinecone, Weaviate, or LangGraph memory).

3. **Cost Tracking (`agentwatch.cost`)**
   - **Why:** Cost tracking is better handled by upstream LLM providers or dedicated FinOps tools. Maintaining custom token counting and pricing models was brittle and distracting.
   - **Action required:** Remove `CostTracker` and related imports from your code. Use platform-specific cost tracking tools.

4. **Legacy Adapters (`agentwatch/adapters/base.py`)**
   - **Why:** We removed unused legacy adapter base classes that were over-abstracted.
   - **Action required:** Use the remaining concrete adapters directly.

5. **Benchmarks Suite (`benchmarks/`)**
   - **Why:** Academic benchmarking added bloat to the repository and CI pipeline without serving our core users.

## Core Scope Focus

AgentWatch now firmly focuses on:
- **Tracing & Telemetry**
- **Safety & Governance**
- **Evaluation & Scoring**

If you relied on the removed features, we recommend pinning to version `0.3.0` until you can migrate to alternative solutions.
