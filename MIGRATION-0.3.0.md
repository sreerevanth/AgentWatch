# Migration to AgentWatch v0.3.0

The v0.3.0 release is a major architectural pivot that focuses entirely on observability, safety, and core API tracking. To achieve this lean architecture, several peripheral components and theoretical features have been removed entirely.

This guide outlines what was removed and how you should migrate away from those components.

## Removed APIs and Features

### 1. `agentwatch.orchestration` 
**Status: Removed**
- **What it was:** A routing engine for multi-agent workflows, managing handoffs and shared contexts between different agent instances.
- **Migration:** You must now handle agent orchestration (e.g., using CrewAI, LangChain, or custom logic) in your own application code. AgentWatch will simply observe and track the agents; it will no longer attempt to control their interactions.

### 2. `agentwatch.memory`
**Status: Removed**
- **What it was:** A complex, graph-based contextual memory storage engine.
- **Migration:** If your agents require persistent episodic or semantic memory, integrate directly with dedicated solutions like Mem0, Zep, or native vector databases (e.g., pgvector, Pinecone). AgentWatch tracks the *events* of retrieval and storage, but does not provide the memory graph.

### 3. `agentwatch.reasoning` (Auditor & Fingerprinting)
**Status: Removed**
- **What it was:** Models and logic for auditing "reasoning styles" and fingerprinting AI behaviors to prevent logic drifts.
- **Migration:** Use external evaluation frameworks (like Ragas or deep-eval) and log the evaluation results back to AgentWatch using the custom event API.

### 4. `agentwatch.cost`
**Status: Removed**
- **What it was:** A dedicated module for highly granular token and dollar cost attribution.
- **Migration:** Token usage should be reported as part of the standard `AgentEvent` metadata. You can aggregate and calculate costs on the dashboard side or using a dedicated FinOps tool.

### 5. `agentwatch.governance.eu_ai_act`
**Status: Removed**
- **What it was:** Speculative logging mechanisms to adhere strictly to theoretical interpretations of the EU AI Act.
- **Migration:** Custom policy enforcement can be built using the standard Circuit Breaker tools by logging your own governance events.

## Breaking Changes to the Core API

### Module Imports
- Imports from `agentwatch.orchestration`, `agentwatch.memory`, `agentwatch.reasoning`, or `agentwatch.cost` will result in a `ModuleNotFoundError`.
- The following specific imports are no longer available:
  - `agentwatch.memory.governance` (used for GDPR erasure)
  - `agentwatch.reasoning.auditor.ReasoningAuditor`
  - `agentwatch.cost.tracker.CostTracker`
  - `agentwatch.cost.reporting` (cost reports and FinOps)
  - `agentwatch.cost.semantic_cache.SemanticCache`

### CLI Commands
- `agentwatch cost report` command is deprecated and will exit with an error message directing users to the migration guide.
- The MCP server's `cost_provider` now returns stub data with a deprecation warning.

### Backward Compatibility Stubs
- `agentwatch.adapters.base` semantic cache functions (`get_semantic_cache`, `set_semantic_cache`, `before_provider_call`, `after_provider_call`) now return no-op stubs for backward compatibility but log deprecation warnings.
- `agentwatch.governance.audit_log.PersistentAuditLog` no longer supports the bloated `SqlAlchemyAuditStore`.

Please update your imports and application logic accordingly to align with this simpler, more stable version of AgentWatch.
