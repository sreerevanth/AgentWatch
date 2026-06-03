```markdown
# AgentWatch Development Patterns

> Auto-generated skill from repository analysis

## Overview
This skill teaches you the core development patterns and conventions used in the AgentWatch Python codebase. You'll learn how to structure code, follow commit and file naming conventions, and implement or enhance API endpoints with proper testing. This guide also covers the main workflow for updating API logic and ensuring code quality with tests.

## Coding Conventions

### File Naming
- Use **snake_case** for all file names.
  - Example: `server_utils.py`, `rate_limiter.py`

### Import Style
- Use **relative imports** within the package.
  - Example:
    ```python
    from .utils import calculate_limit
    ```

### Export Style
- Use **named exports** (i.e., define functions/classes and import them by name).
  - Example:
    ```python
    # In agentwatch/api/server.py
    def handle_request(...):
        ...
    ```

### Commit Messages
- Use **conventional commit** style.
- Prefix with `fix` for bug fixes.
- Keep messages concise (average 62 characters).
  - Example:  
    ```
    fix: handle edge case in rate limiting logic
    ```

## Workflows

### API Endpoint Enhancement with Tests
**Trigger:** When you want to add, fix, or enhance an API endpoint and verify it with tests.  
**Command:** `/update-api-endpoint`

1. **Edit or enhance the API endpoint implementation**  
   - Open `agentwatch/api/server.py`.
   - Locate the relevant endpoint function or add a new one.
   - Example:
     ```python
     # agentwatch/api/server.py
     def get_user_status(user_id):
         # New or updated logic here
         ...
     ```
2. **Update or add corresponding tests**  
   - Open or create `tests/test_rate_limiting.py`.
   - Write or update test cases to cover your changes.
   - Example:
     ```python
     # tests/test_rate_limiting.py
     def test_get_user_status():
         assert get_user_status(123) == "active"
     ```
3. **Run tests to ensure correctness**  
   - Use your preferred test runner (e.g., pytest).
   - Example:
     ```
     pytest tests/test_rate_limiting.py
     ```
4. **Commit your changes**  
   - Use a conventional commit message.
   - Example:
     ```
     fix: update get_user_status endpoint and add tests
     ```

## Testing Patterns

- **Test Framework:** Not explicitly specified; likely uses `pytest` or similar.
- **Test File Pattern:** Test files are named with the pattern `*.test.ts` (possibly a typo or legacy pattern; Python tests are usually `test_*.py`).
- **Test Location:** Place tests in the `tests/` directory.
- **Test Example:**
  ```python
  # tests/test_rate_limiting.py
  def test_rate_limit_exceeded():
      assert rate_limit(user_id=1) is False
  ```

## Commands
| Command                | Purpose                                                      |
|------------------------|--------------------------------------------------------------|
| /update-api-endpoint   | Enhance or fix an API endpoint and update corresponding tests |

```