# Contributing to AgentWatch

Thank you for your interest in contributing to AgentWatch 🚀

AgentWatch is an open-source reliability, safety, and observability platform for AI agents.

We welcome contributors of all experience levels, from first-time open-source contributors to experienced engineers.

---

# Ways to Contribute

You can contribute through:

- Bug fixes
- New features
- Documentation improvements
- Performance optimizations
- Testing and quality improvements
- Developer tooling
- Integrations
- Security improvements
- Design and user experience enhancements

Every contribution matters.

---

# Community First

We want AgentWatch to be a collaborative and welcoming project.

Please:

- Be respectful
- Be constructive
- Be open to feedback
- Help other contributors when possible

We're building this together.

---

# Community & Support

Join the AgentWatch community:

💬 Discord:
https://discord.com/invite/ZbQ9m9HtnE

The Discord server is the best place for:

- Asking development questions
- Discussing features before building them
- Getting help with setup issues
- Coordinating large contributions
- Following project updates
- Connecting with other contributors

If you're planning a larger feature or architectural change, we strongly recommend discussing it in Discord first.

Open-source works best when contributors communicate early.

---

# Before You Start

## Check Existing Work

Before creating an issue or pull request:

- Search existing issues
- Search existing pull requests
- Check project discussions
- Verify the issue has not already been reported

Duplicate reports create unnecessary review overhead.

---

## Discuss Large Changes First

For significant features, architectural changes, or major refactors:

Please open an issue first.

This helps ensure:

- The feature aligns with project goals
- Development effort is not wasted
- Maintainers can provide guidance early

---

# Local Development Setup

## Clone Your Fork

```bash
git clone https://github.com/YOUR_USERNAME/AgentWatch.git
cd AgentWatch
```

## Create a Branch

```bash
git checkout -b feature/my-feature
```

Examples:

```text
fix/session-memory-bug
feat/slack-alerts
docs/api-guide
```

Do not commit directly to `main`.

---

# Backend Setup

```bash
python -m pip install -e ".[dev]"
```

## Windows

Windows requires a few extra steps. Follow this section carefully.

### Step 1 - Verify Python is installed

Open Command Prompt or PowerShell and run:

```powershell
python --version
```

You should see `Python 3.10` or higher. If not, download it from [python.org](https://www.python.org/downloads/).

> During installation, make sure to check **"Add Python to PATH"**.

---

### Step 2 - Create a virtual environment

```powershell
python -m venv venv
```

This creates a `venv/` folder in your project directory.

---

### Step 3 - Activate the virtual environment

**Command Prompt:**

```cmd
venv\Scripts\activate
```

**PowerShell:**

```powershell
venv\Scripts\Activate.ps1
```

> If PowerShell blocks the script with an execution policy error, run this first:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```
> Then try activating again.

Once activated, your prompt will show `(venv)` at the start.

---

### Step 4 - Install dependencies

```powershell
python -m pip install -e ".[dev]"
```

---

### Step 5 - Verify the setup

```powershell
python -c "import agentwatch; print('Setup successful')"
```

---

### Deactivating the virtual environment

```powershell
deactivate
```

---

### Common Windows Issues

| Problem | Fix |
|---|---|
| `python` not found | Re-install Python and check "Add to PATH" |
| `Activate.ps1` blocked | Run `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser` |
| `pip` not found inside venv | Run `python -m pip install --upgrade pip` |
| `pip install` permission error | Ensure venv is activated |
| Git line ending warnings | Run `git config --global core.autocrlf true` |


---

# Frontend Setup

```bash
cd frontend
npm install
```

---

# Start Development Environment

```bash
docker compose up -d
```

Run backend:

```bash
python demo.py
```

Frontend:

```text
http://localhost:3000
```

---

# Project Structure

```text
AgentWatch/
├── agentwatch/
├── frontend/
├── tests/
├── docs/
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

---

# Issue Guidelines

## High Quality Issues

Good issues include:

- Clear problem description
- Reproduction steps
- Expected behavior
- Actual behavior
- Relevant logs or screenshots
- Environment information

Example:

```text
Expected:
Session should reconnect automatically

Actual:
Connection remains disconnected after network recovery
```

---

## Enhancement Requests

Enhancement requests should answer:

### What problem exists?

Explain the current limitation.

### Why is it valuable?

Describe the impact.

### What is the proposed solution?

Provide a reasonable implementation direction.

---

## Low Quality Issues

Issues may be closed if they:

- Cannot be reproduced
- Lack sufficient details
- Duplicate existing reports
- Are generated from automated scans without verification
- Are speculative without evidence

Quality matters more than quantity.

---

# Pull Request Guidelines

## Keep PRs Focused

A pull request should solve one logical problem.

Good examples:

- Fix one bug
- Add one feature
- Improve one documentation area

Avoid:

- Massive unrelated refactors
- Multiple independent features
- Formatting-only changes mixed with functional changes

---

## Pull Request Requirements

Before opening a PR:

- Code builds successfully
- Tests pass
- New tests are added when appropriate
- Documentation is updated when needed
- No unrelated files are modified

---

## Pull Request Title Format

Use conventional commits.

Examples:

```text
fix: resolve websocket reconnect issue

feat: add reasoning confidence dashboard

docs: improve installation guide

test: add safety engine integration coverage
```

---

## Pull Request Description

Use:

```md
## Summary

Short explanation of the change.

## Changes

- Change 1
- Change 2

## Validation

- Ran tests
- Tested locally
- Verified frontend build
```

---

# Code Quality Standards

## Python

- Follow PEP8
- Prefer type hints
- Write readable code
- Keep functions focused
- Avoid unnecessary abstractions

---

## Frontend

- Keep components modular
- Minimize dependencies
- Maintain UI consistency
- Avoid unnecessary complexity

---

# Testing

Run before submitting:

```bash
ruff check .
pytest
```

Frontend:

```bash
cd frontend
npm run build
```

Pull requests with failing checks will not be merged.

---

# Documentation Contributions

Documentation contributions are highly encouraged.

Examples:

- Tutorials
- Architecture explanations
- Troubleshooting guides
- Integration examples
- Setup improvements

Documentation-only contributions are welcome.

---

# Security Issues

Please do not open public issues for security vulnerabilities.

Instead, contact the maintainers privately through GitHub Security Advisories or project contact channels.

---

# Review Process

All pull requests are reviewed by maintainers.

Reviews may request:

- Additional tests
- Documentation updates
- Code improvements
- Architectural adjustments

Review feedback is a normal part of the process.

---

# Recognition

Whether you:

- Fix a typo
- Improve documentation
- Add a test
- Ship a major feature

your contribution is appreciated.

Thank you for helping build AgentWatch ❤️
