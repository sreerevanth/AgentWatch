```markdown
# AgentWatch Development Patterns

> Auto-generated skill from repository analysis

## Overview
This skill provides guidance on the development conventions and workflows used in the AgentWatch Python codebase. It covers file naming, import/export styles, commit message patterns, documentation update workflows, and testing practices. Use this as a reference for contributing to or maintaining the repository.

## Coding Conventions

### File Naming
- Use **snake_case** for all Python file names.
  - Example: `agent_manager.py`, `data_loader.py`

### Import Style
- Use **relative imports** within the package.
  - Example:
    ```python
    from .utils import parse_agent_config
    ```

### Export Style
- Use **named exports** (explicitly define what is exported).
  - Example:
    ```python
    __all__ = ['AgentManager', 'load_agents']
    ```

### Commit Messages
- Follow **conventional commit** patterns.
- Use prefixes such as `docs:` for documentation and `fix:` for bug fixes.
- Keep commit messages concise but descriptive (average ~78 characters).
  - Example:
    ```
    docs: update NEXT_15_MIGRATION.md with new migration steps
    fix: resolve agent status update race condition
    ```

## Workflows

### Documentation Update (Single File)
**Trigger:** When documentation needs to be updated for a migration, feature, or review feedback.  
**Command:** `/update-doc`

1. Edit the relevant markdown file in the documentation directory (e.g., `frontend/NEXT_15_MIGRATION.md`).
2. Commit the change with a `docs:` prefix and a brief description.
   - Example:
     ```
     docs: clarify migration steps in NEXT_15_MIGRATION.md
     ```
3. Push your changes and open a pull request if required.

## Testing Patterns

- **Framework:** Unknown (no explicit framework detected).
- **File Pattern:** Test files follow the `*.test.ts` naming convention, suggesting some frontend or TypeScript-based testing.
  - Example: `agent_status.test.ts`
- **Note:** No Python test framework detected; consider standardizing on `pytest` or similar for backend tests.

## Commands
| Command      | Purpose                                                  |
|--------------|----------------------------------------------------------|
| /update-doc  | Update or add documentation in a single markdown file    |
```