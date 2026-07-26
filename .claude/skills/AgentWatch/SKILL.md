```markdown
# AgentWatch Development Patterns

> Auto-generated skill from repository analysis

## Overview
This skill teaches you the core development patterns and conventions used in the AgentWatch Python codebase. You'll learn how to structure files, write imports and exports, and follow commit and testing patterns. This guide is ideal for contributors looking to maintain consistency and quality in AgentWatch.

## Coding Conventions

### File Naming
- Use **snake_case** for all file and module names.

  **Example:**
  ```
  agent_manager.py
  user_profile_handler.py
  ```

### Import Style
- Use **relative imports** within the package.

  **Example:**
  ```python
  from .utils import parse_agent_config
  from .models.agent import Agent
  ```

### Export Style
- Use **named exports** (i.e., define and export specific classes, functions, or variables).

  **Example:**
  ```python
  # agent_manager.py
  class AgentManager:
      pass

  def create_agent():
      pass
  ```

### Commit Patterns
- Commit messages are **freeform** (no strict prefix required).
- Average commit message length: ~48 characters.

  **Example:**
  ```
  Add support for agent status monitoring
  Fix bug in agent registration logic
  ```

## Workflows

### Adding a New Agent Feature
**Trigger:** When you need to introduce a new feature related to agent functionality.
**Command:** `/add-agent-feature`

1. Create a new Python file using snake_case (e.g., `agent_feature.py`).
2. Implement the feature using relative imports for dependencies.
3. Export new classes or functions explicitly.
4. Write or update tests in a corresponding `*.test.*` file.
5. Commit your changes with a clear, descriptive message.

### Refactoring Existing Code
**Trigger:** When improving or restructuring existing code.
**Command:** `/refactor-code`

1. Identify the module(s) to refactor.
2. Use relative imports for any new or updated dependencies.
3. Ensure file names remain in snake_case.
4. Update or add tests as needed.
5. Commit with a message summarizing the refactor.

### Writing and Running Tests
**Trigger:** When adding new features or fixing bugs.
**Command:** `/run-tests`

1. Create or update test files using the pattern `*.test.*` (e.g., `agent_manager.test.py`).
2. Write tests for all new or changed functionality.
3. Use the project's preferred (unknown) test framework.
4. Run the tests to ensure all pass before committing.

## Testing Patterns

- Test files follow the pattern `*.test.*` (e.g., `feature.test.py`).
- The specific test framework is not detected; check existing tests for conventions.
- Place tests alongside or within a dedicated test directory, as per project structure.

  **Example:**
  ```
  agent_manager.test.py
  ```

## Commands
| Command            | Purpose                                            |
|--------------------|----------------------------------------------------|
| /add-agent-feature | Scaffold and implement a new agent-related feature |
| /refactor-code     | Refactor existing code for clarity or performance  |
| /run-tests         | Run all tests before committing changes            |
```
