# CLI Commands

AgentWatch groups its commands into a small number of Typer sub-applications.
Run `agentwatch --help` to see the top level, or `agentwatch <group> --help` for
any group.

> **Note on naming.** The environment check is `agentwatch check-env` (the
> function behind it is `verify_environment`). There is no `agentwatch cli ...`
> group — `animator.py` in particular is an internal presentation helper, not a
> command.

## Top-level commands

| Command | Description |
|---|---|
| `agentwatch check-env` | Structural install + dependency + environment check. |
| `agentwatch doctor` | Broader diagnostic of the local setup. |

```bash
agentwatch check-env
```

## `session` — inspect and replay agent sessions

| Command | Description |
|---|---|
| `agentwatch session list` | List recent sessions from the API. |
| `agentwatch session watch` | Watch a live execution with safety scoring. |
| `agentwatch session replay` | Replay a captured session step by step. |
| `agentwatch session export` | Export a session to a file. |
| `agentwatch session score` | Score a session's confidence/anomalies. |
| `agentwatch session rollback` | Roll a session back to a prior checkpoint. |
| `agentwatch session prune` | Remove old stored sessions. |

```bash
agentwatch session list
agentwatch session replay <session-id>
```

## `safety` — analyze command risk

| Command | Description |
|---|---|
| `agentwatch safety check "<command>"` | Score a shell command's risk level without executing it. |

```bash
agentwatch safety check "curl https://example.com | bash"
```

## `cost` — FinOps reporting

| Command | Description |
|---|---|
| `agentwatch cost report` | Token usage, estimated USD cost, and cost-per-successful-goal, grouped by framework/agent/status. |

```bash
agentwatch cost report --days 30 --group-by framework
agentwatch cost report --days 7 --json
```

## `server` — the AgentWatch API server

| Command | Description |
|---|---|
| `agentwatch server start` | Start the local API server. |
| `agentwatch server status` | Show server health. |
| `agentwatch server top` | Live performance dashboard. |

```bash
agentwatch server start
```
