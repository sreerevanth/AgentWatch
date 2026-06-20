```markdown
# AgentWatch Development Patterns

> Auto-generated skill from repository analysis

## Overview
This skill covers the development patterns and conventions used in the AgentWatch Python codebase. It documents file organization, code style, commit practices, and testing approaches to help contributors maintain consistency and quality.

## Coding Conventions

### File Naming
- Use **snake_case** for all file names.
  - Example: `agent_manager.py`, `data_collector.py`

### Import Style
- Use **relative imports** within the package.
  - Example:
    ```python
    from .utils import parse_config
    from .models.agent import Agent
    ```

### Export Style
- Use **named exports** by explicitly specifying what is exported from a module.
  - Example:
    ```python
    __all__ = ["AgentManager", "Agent"]
    ```

### Commit Messages
- Follow **conventional commit** style.
- Use the `feat` prefix for new features.
- Keep commit messages concise (average ~35 characters).
  - Example:
    ```
    feat: add agent status monitoring
    ```

## Workflows

### Adding a New Feature
**Trigger:** When implementing a new capability or module  
**Command:** `/add-feature`

1. Create a new Python file using snake_case naming.
2. Use relative imports to reference internal modules.
3. Implement the feature using clear, modular code.
4. Add named exports as needed.
5. Write or update tests in a corresponding `*.test.*` file.
6. Commit using the `feat:` prefix and a concise description.

### Refactoring Code
**Trigger:** When improving or restructuring existing code  
**Command:** `/refactor`

1. Identify the target module or function.
2. Refactor code while maintaining relative imports and named exports.
3. Update or add tests to cover changes.
4. Commit changes with a clear message (e.g., `feat: refactor agent logic`).

### Writing Tests
**Trigger:** When adding or updating tests  
**Command:** `/write-test`

1. Create or update a test file matching the pattern `*.test.*` (e.g., `agent_manager.test.py`).
2. Write tests for new or modified features.
3. Use the same coding conventions as production code.
4. Run tests to ensure correctness.

## Testing Patterns

- Test files follow the pattern `*.test.*` (e.g., `data_collector.test.py`).
- The testing framework is not specified; use standard Python testing tools (e.g., `unittest`, `pytest`) as appropriate.
- Place tests alongside or near the modules they cover.
- Example test file structure:
  ```python
  import unittest
  from .agent_manager import AgentManager

  class TestAgentManager(unittest.TestCase):
      def test_agent_creation(self):
          manager = AgentManager()
          self.assertIsNotNone(manager)
  ```

## Commands
| Command        | Purpose                                   |
|----------------|-------------------------------------------|
| /add-feature   | Start workflow for adding a new feature   |
| /refactor      | Start workflow for refactoring code       |
| /write-test    | Start workflow for writing or updating tests |
```
