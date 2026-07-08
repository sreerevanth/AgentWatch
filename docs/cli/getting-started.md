# Getting Started

## Install

AgentWatch requires Python 3.10+.

```bash
pip install agentwatch
```

To work from a checkout of the repository:

```bash
git clone https://github.com/sreerevanth/AgentWatch.git
cd AgentWatch
pip install -e ".[dev]"
```

## Verify your environment

Before anything else, confirm your install is healthy:

```bash
agentwatch check-env
```

This runs a structural check of the install, confirms required dependencies are
importable, and reports on relevant environment variables. For a broader
diagnostic, use:

```bash
agentwatch doctor
```

## Your first commands

List recent agent sessions (requires the API server — see below):

```bash
agentwatch session list
```

Score the risk of a shell command without running it:

```bash
agentwatch safety check "rm -rf /"
```

Sample output:

```
        S E C U R I T Y   R E P O R T
  Risk: CRITICAL
  [!] Recursive deletion of critical filesystem path
```

Report token usage and estimated spend across frameworks over the last 30 days:

```bash
agentwatch cost report --days 30 --group-by framework
```

## Running the API server

Several commands (`session list`, `session watch`, `cost report`) read from the
AgentWatch API. Start it locally with:

```bash
agentwatch server start
```

Then, in another terminal, check its health or open the live dashboard:

```bash
agentwatch server status
```

## Getting help

Every command and group supports `--help`:

```bash
agentwatch --help
agentwatch session --help
agentwatch safety check --help
```
