```markdown
# AgentWatch Development Patterns

> Auto-generated skill from repository analysis

## Overview
This skill teaches you the core development patterns and conventions used in the AgentWatch Python codebase. You'll learn about file organization, import/export styles, commit message structure, and how to write and discover tests. These patterns help maintain consistency and readability across the project.

## Coding Conventions

### File Naming
- Use **snake_case** for all file names.
  - Example: `agent_manager.py`, `data_loader.py`

### Import Style
- Use **relative imports** within the package.
  - Example:
    ```python
    from .utils import parse_config
    from ..core.agent import Agent
    ```

### Export Style
- Use **named exports** (explicitly specify what is exported).
  - Example:
    ```python
    __all__ = ["AgentManager", "load_agents"]
    ```

### Commit Messages
- Follow **conventional commit** style, using prefixes like `fix`.
  - Example:
    ```
    fix: handle agent disconnects gracefully in manager
    ```

## Workflows

### Fixing a Bug
**Trigger:** When you identify and resolve a bug in the codebase  
**Command:** `/fix-bug`

1. Create a new branch for your fix.
2. Make the necessary code changes.
3. Write or update tests to cover the bug fix.
4. Commit your changes using the `fix:` prefix and a concise description.
    - Example: `fix: correct agent status update logic`
5. Push your branch and open a pull request.

### Adding a New Module
**Trigger:** When you need to add new functionality as a separate module  
**Command:** `/add-module`

1. Create a new Python file using snake_case naming.
    - Example: `data_processor.py`
2. Implement your module, using relative imports for dependencies.
3. Add named exports via `__all__`.
4. Write corresponding tests in a file matching `*.test.*`.
5. Commit your changes with an appropriate prefix (e.g., `feat:`).

### Writing and Running Tests
**Trigger:** When you add or modify code and need to ensure correctness  
**Command:** `/run-tests`

1. Create test files using the `*.test.*` pattern.
    - Example: `agent_manager.test.py`
2. Write test cases for your code.
3. Use the project's preferred test runner (framework is unspecified; check project docs or use `pytest` as a default).
4. Run the tests and ensure all pass before committing.

## Testing Patterns

- **Test File Naming:** Use `*.test.*` for test files.
    - Example: `utils.test.py`
- **Framework:** Not explicitly specified; likely to use standard Python testing tools (e.g., `unittest` or `pytest`).
- **Location:** Place test files alongside or near the code they test.
- **Example Test:**
    ```python
    # agent_manager.test.py
    from .agent_manager import AgentManager

    def test_agent_initialization():
        manager = AgentManager()
        assert manager.is_initialized()
    ```

## Commands
| Command      | Purpose                                      |
|--------------|----------------------------------------------|
| /fix-bug     | Start the bug fix workflow                   |
| /add-module  | Add a new module to the codebase             |
| /run-tests   | Run all tests in the repository              |
```
