# Developer Setup Guide

## Environment Requirements
Prepare a Python environment running exactly version 3.12 (newer versions are currently not verified in CI):
```bash
python --version
```

## Installation
1. Clone the repository fork:
   ```bash
   git clone https://github.com/sreerevanth/AgentWatch.git
   ```
2. Navigate and install dependencies:
   ```bash
   cd AgentWatch
   pip install -e ".[dev]"
   ```
3. Run verification tests:
   ```bash
   python -m pytest tests/
   ```
