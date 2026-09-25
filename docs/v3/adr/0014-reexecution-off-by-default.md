# ADR-0014: Server-side re-execution is off by default

- Status: Accepted
- Date: 2026-09-25

## Context

L2/L3 replay, branch execution and executed counterfactuals re-run the *recorded command* of a run on the machine that runs AgentWatch. Through the HTTP API, that turns "read access to a run" into "execute this command on the server".

## Decision

- The CLI can re-execute, because the user is running their own recorded program locally.
- The API refuses L2/L3 replay and branch execution with 403 unless `AGENTWATCH_ALLOW_REEXECUTION=1`.
- Counterfactual requests fall back to history-based estimates (`MODEL_ESTIMATED` / `UNKNOWN`) when re-execution is off.
- L0/L1 replay are always available, because they execute nothing.

## Consequences

- Operators must opt in per deployment.
- The UI (LAB) shows which levels are enabled.
