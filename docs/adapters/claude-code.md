# Claude Code Adapter

AgentWatch provides a first-class CLI wrapper for [Claude Code](https://github.com/anthropics/claude-code), allowing you to observe its reasoning steps, tool calls, and apply safety policies without modifying any code.

## Usage

Simply prefix your `claude` command with `agentwatch watch`:

```bash
agentwatch watch "Build me a React component for a weather dashboard"
```

## How It Works

1. **Subprocess Interception**: AgentWatch runs Claude Code as a child process.
2. **Stream Parsing**: It captures the terminal output and parses reasoning traces in real-time.
3. **Safety Enforcement**: If Claude Code attempts a dangerous command (e.g., `rm -rf /`), AgentWatch identifies the intent and can block the execution based on your policy.
4. **Dashboard Integration**: Every step is streamed over WebSockets to your local AgentWatch dashboard.

## Configuration Options

### Pinning a Model
By default, AgentWatch respects the model Claude Code is configured to use. You can override this for auditing purposes:

```bash
agentwatch watch "..." --model claude-3-5-sonnet-20241022
```

### Applying a Safety Policy
Use a custom policy defined in your AgentWatch server:

```bash
agentwatch watch "..." --policy strict-production
```

## Benefits for Claude Code Users

- **Auditability**: See exactly what Claude did while you were away from the terminal.
- **Safety**: Prevent accidental file deletions or credential leaks.
- **Cost Tracking**: Monitor the token cost of complex coding tasks.
