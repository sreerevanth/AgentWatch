```markdown
# AgentWatch Development Patterns

> Auto-generated skill from repository analysis

## Overview
This skill teaches the core development patterns and conventions used in the AgentWatch Python codebase. It covers file naming, import/export styles, commit message standards, and testing patterns. By following these guidelines, contributors can ensure consistency and maintainability in the project.

## Coding Conventions

### File Naming
- Use **camelCase** for all file names.
  - Example: `agentManager.py`, `userSession.py`

### Import Style
- Use **relative imports** within the codebase.
  - Example:
    ```python
    from .utils import parseData
    from ..models import Agent
    ```

### Export Style
- Use **named exports** (explicitly define what is exported from a module).
  - Example:
    ```python
    # In agentManager.py
    def startAgent():
        pass

    def stopAgent():
        pass

    __all__ = ['startAgent', 'stopAgent']
    ```

### Commit Messages
- Follow **conventional commit** standards.
- Use prefixes like `fix` for bug fixes.
  - Example: `fix: resolve agent session timeout issue`

## Workflows

### Fixing a Bug
**Trigger:** When you identify and resolve a bug in the codebase  
**Command:** `/fix-bug`

1. Create a new branch for your fix.
2. Make code changes following the coding conventions.
3. Write or update tests as needed.
4. Commit your changes using the `fix:` prefix and a clear description.
    - Example: `fix: handle missing agent configuration`
5. Push your branch and open a pull request for review.

### Adding a New Feature
**Trigger:** When implementing a new feature or enhancement  
**Command:** `/add-feature`

1. Create a new branch for your feature.
2. Implement the feature using camelCase file naming and relative imports.
3. Export new functions or classes using named exports.
4. Write tests in a file matching the `*.test.*` pattern.
5. Commit your changes with a descriptive message (e.g., `feat: add agent monitoring`).
6. Push your branch and open a pull request.

## Testing Patterns

- Test files follow the `*.test.*` naming pattern.
  - Example: `agentManager.test.py`
- The specific testing framework is not detected; use standard Python testing practices (e.g., `unittest` or `pytest`).
- Place test cases near the code they test for clarity and maintainability.

  Example test file:
  ```python
  # agentManager.test.py
  import unittest
  from .agentManager import startAgent

  class TestAgentManager(unittest.TestCase):
      def test_start_agent(self):
          self.assertTrue(startAgent())
  ```

## Commands
| Command      | Purpose                                      |
|--------------|----------------------------------------------|
| /fix-bug     | Start the workflow for fixing a bug          |
| /add-feature | Begin the process of adding a new feature    |
```
