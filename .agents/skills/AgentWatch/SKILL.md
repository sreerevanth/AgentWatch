```markdown
# AgentWatch Development Patterns

> Auto-generated skill from repository analysis

## Overview
AgentWatch is a Python-based codebase focused on agent monitoring and API management. The repository emphasizes clear structure, consistent coding conventions, and includes workflows for maintaining robust API endpoint features such as rate limiting. While no specific framework is detected, the repository follows Python best practices and includes a set of automated tests.

## Coding Conventions

- **File Naming:**  
  Use `snake_case` for all file and module names.  
  *Example:*  
  ```
  agentwatch/api/server.py
  tests/test_rate_limiting.py
  ```

- **Import Style:**  
  Use relative imports within packages.  
  *Example:*  
  ```python
  from .utils import get_config
  ```

- **Export Style:**  
  Use named exports; avoid wildcard (`*`) imports and exports.  
  *Example:*  
  ```python
  def rate_limit_handler(...):
      ...
  ```

- **Commit Messages:**  
  - Mixed types, commonly prefixed with `fix`
  - Average length: ~67 characters  
  *Example:*  
  ```
  fix: update rate limiting logic to handle burst requests
  ```

## Workflows

### API Endpoint Rate Limiting Update
**Trigger:** When someone wants to add, fix, or enhance rate limiting on an API endpoint.  
**Command:** `/update-rate-limit`

1. **Modify or extend rate limiting logic**  
   Edit `agentwatch/api/server.py` to implement the new or updated rate limiting logic.  
   *Example:*  
   ```python
   # agentwatch/api/server.py
   def check_rate_limit(request):
       # Updated logic here
       if too_many_requests(request):
           return error_response("Rate limit exceeded", status=429)
   ```

2. **Update or add tests**  
   Edit or create tests in `tests/test_rate_limiting.py` to cover your changes.  
   *Example:*  
   ```python
   # tests/test_rate_limiting.py
   def test_rate_limit_exceeded(client):
       response = client.get('/api/endpoint')
       assert response.status_code == 429
   ```

3. **Ensure correct error contracts and headers**  
   Make sure the API returns the correct error messages and headers (like `Retry-After`) when rate limits are exceeded.  
   *Example:*  
   ```python
   assert response.headers['Retry-After'] == '60'
   ```

## Testing Patterns

- **Framework:** Unknown (no explicit framework detected)
- **File Pattern:** Test files are named with the pattern `*.test.ts` (note: this is a TypeScript convention; Python tests are in `tests/` directory, e.g., `test_rate_limiting.py`)
- **Test Structure:**  
  - Place tests in the `tests/` directory.
  - Name test files using `test_` prefix and snake_case.
  - Use standard Python test assertions.
  *Example:*  
  ```python
  def test_feature_behavior():
      assert some_function() == expected_result
  ```

## Commands

| Command             | Purpose                                                         |
|---------------------|-----------------------------------------------------------------|
| /update-rate-limit  | Implements or updates rate limiting logic for an API endpoint   |
```