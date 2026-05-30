# Contributing to AgentWatch

First off — thank you for contributing to AgentWatch 🚀

We welcome:
- bug fixes
- new features
- documentation improvements
- integrations
- performance optimizations
- developer tooling improvements

Whether this is your first open-source contribution or your hundredth, you're welcome here.

---

# Before You Start

## 1. Fork the Repository

Click the **Fork** button on GitHub and clone your fork locally.

```bash
git clone https://github.com/YOUR_USERNAME/AgentWatch.git
cd AgentWatch
```

---

## 2. Create a New Branch

Please create a dedicated branch for your changes.

```bash
git checkout -b feature/my-feature
```

Examples:
- `fix/session-memory-bug`
- `docs/getting-started-guide`
- `feature/slack-alerts`

Avoid committing directly to `main`.

---

# Local Development Setup

## Backend Setup

```bash
python -m pip install -e ".[dev]"
```

## Frontend Setup

```bash
cd frontend
npm install
```

## Start Development Environment

```bash
docker compose up -d
```

Run backend:

```bash
python demo.py
```

Frontend dashboard:

```text
http://localhost:3000
```

---

# Project Structure

```text
AgentWatch/
├── agentwatch/
├── frontend/
├── docs/
├── tests/
├── demo.py
├── docker-compose.yml
└── README.md
```

---

# Contribution Guidelines

## Keep Pull Requests Focused

Please keep PRs limited to a single logical change.

Good:
- fix one bug
- improve one feature
- add one documentation section

Avoid:
- unrelated refactors
- multiple large features in one PR

---

## Write Clear Commit Messages

Examples:

```text
fix: resolve websocket reconnect issue
docs: add getting started tutorial
feat: add confidence trend visualization
```

---

## Run Checks Before Submitting

### Python

```bash
ruff check .
pytest
```

### Frontend

```bash
cd frontend
npm run build
```

---

# Pull Request Process

## Before Opening a PR

Please ensure:
- code builds successfully
- tests pass
- no unrelated files are modified
- documentation is updated if needed

---

## PR Title Format

Use conventional-style titles:

```text
fix: resolve memory leak in session tracker
docs: improve installation instructions
feat: add PagerDuty alert support
```

---

## PR Description Template

```md
## Summary
Brief explanation of changes

## What Changed
- item 1
- item 2

## Validation
- tested locally
- ran frontend build
- ran tests
```

---

# Documentation Contributions

Documentation improvements are highly appreciated ❤️

You can contribute:
- tutorials
- examples
- architecture explanations
- setup fixes
- troubleshooting guides

Docs-only PRs are welcome.

---

# Reporting Issues

When opening an issue, include:
- expected behavior
- actual behavior
- logs/screenshots if applicable
- reproduction steps
- environment details

---

# Coding Style

## Python
- follow PEP8
- prefer type hints
- keep functions focused and readable

## Frontend
- keep components modular
- avoid unnecessary dependencies
- maintain consistent UI patterns

---

# Need Help?

If you're stuck:
- open a discussion
- comment on an issue
- ask questions in your PR

We'd rather help early than review a huge broken PR later 😄

---

# Recognition

All contributors matter — whether you fixed a typo, improved docs, or shipped a major feature.

Thanks for helping improve AgentWatch 🚀