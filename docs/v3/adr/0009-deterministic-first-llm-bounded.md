# ADR-0009: Deterministic algorithms first; LLMs only as bounded, grounded helpers

- Status: Proposed
- Date: 2026-09-25

## Context

LLMs are good at translating questions and proposing hypotheses. They are bad at being ground truth. v0.2 uses an LLM judge for reasoning scores and ships heuristic proxies labelled as risk (D7). v3's value depends on explanations that are *faithful to evidence*.

## Decision

LLMs are permitted only for:

1. **NL → structured query plan** compilation (QUERY). The plan is shown to the user, then executed deterministically.
2. **Rendering** structured results into prose. The prose may only reference facts present in the result object. Each sentence carries evidence refs. A faithfulness check (every number and id in the prose appears in the result) runs before display.
3. **Hypothesis proposal.** Output becomes `CausalHypothesis(status=PROPOSED)` with no evidence class (ADR-0007).
4. **Optional semantic similarity** for artifacts (embedding models), versioned, and only as a HEURISTIC or MODEL basis.

LLMs are prohibited for:

- creating relations, evidence classes, metrics, labels used as ground truth, or benchmark scores;
- anything a deterministic algorithm solves: pairing, alignment, reachability, statistics.

The whole system runs without an LLM configured. NL features degrade to the deterministic query parser (adapted from `memory/graph_query.py`).

## Consequences

- Explanations are slower to build and less fluent, and they are trustworthy.
- LLM baselines in AWBench record model id, prompt hash and temperature, and are compared rather than trusted.
