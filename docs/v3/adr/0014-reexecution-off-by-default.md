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
- **Enabling it grants command execution to every client that can ingest observations.** The command that is re-run is the `command` attribute of the run, and a run's attributes come from its observations. Any client allowed to `POST /api/v3/observations` (or `/v1/traces`) can therefore record a run whose command it chose, then request its replay. The argument validator (`cli._utils`, no shell metacharacters) narrows what can be passed but is not a sandbox. Enable re-execution only for trusted, single-user deployments where every ingesting client is trusted. The server logs a warning at start when it is on (added 2026-09-27).
- The UI (LAB) shows which levels are enabled.
