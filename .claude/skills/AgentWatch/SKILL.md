```markdown
# AgentWatch Development Patterns

> Auto-generated skill from repository analysis

## Overview
This skill teaches you how to contribute effectively to the AgentWatch Python codebase. You'll learn the project's coding conventions, commit patterns, and how to follow key workflows for updating CI pipelines and enhancing security modules. This guide is ideal for developers looking to make high-quality, consistent contributions to AgentWatch.

## Coding Conventions

- **Language:** Python (no framework detected)
- **File Naming:** Uses camelCase for file names.
  - Example: `owaspScanner.py`, `reportOnPr.yml`
- **Import Style:** Relative imports are preferred.
  - Example:
    ```python
    from .utils import parseReport
    ```
- **Export Style:** Named exports are used (explicitly listing exported functions/classes).
  - Example:
    ```python
    __all__ = ['scan_for_vulnerabilities', 'generate_report']
    ```
- **Commit Patterns:** Follows [Conventional Commits](https://www.conventionalcommits.org/) with prefixes like `ci` and `fix`.
  - Example:
    ```
    ci: split test workflow for PR and main branches
    fix: correct XSS detection logic in OWASP module
    ```

## Workflows

### Update GitHub Actions Workflow
**Trigger:** When you need to change, split, or harden CI workflows for PR testing or reporting.  
**Command:** `/update-ci-workflow`

1. Edit one or more files in `.github/workflows/` (e.g., `report-on-pr.yml`, `test-on-pr.yml`).
2. Make improvements such as splitting workflows, pinning action versions, or updating logic.
3. Commit your changes with a descriptive message about the CI improvement or fix.
   - Example:
     ```
     ci: pin actions/checkout to v3 in test-on-pr.yml
     ```
4. Open a pull request for review.

**Example:**
```yaml
# .github/workflows/test-on-pr.yml
name: Test on PR
on: [pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run tests
        run: pytest
```

---

### Security Feature or Fix in OWASP Module
**Trigger:** When you want to add, fix, or improve security scanning logic in the OWASP module.  
**Command:** `/update-owasp-security`

1. Edit `agentwatch/security/owasp.py` to add or fix security logic.
2. Optionally, update or add tests in `tests/test_owasp_security.py` to cover your changes.
3. Commit your changes with a message describing the security update.
   - Example:
     ```
     fix: improve SQL injection detection in OWASP scanner
     ```
4. Open a pull request for review.

**Example:**
```python
# agentwatch/security/owasp.py
def scan_for_sql_injection(input_str):
    # Improved detection logic
    suspicious_patterns = ["'", '"', '--', ';', '/*', '*/', 'xp_']
    return any(p in input_str for p in suspicious_patterns)
```

```python
# tests/test_owasp_security.py
def test_scan_for_sql_injection():
    assert scan_for_sql_injection("SELECT * FROM users WHERE name = 'admin'--")
```

## Testing Patterns

- **Test File Pattern:** Test files are named with the pattern `*.test.*` (e.g., `owaspSecurity.test.py`).
- **Testing Framework:** Not explicitly detected; likely uses `pytest` or standard Python `unittest`.
- **Test Location:** Tests are located in the `tests/` directory.
- **Example Test:**
  ```python
  # tests/owaspSecurity.test.py
  def test_xss_detection():
      assert scan_for_xss('<script>alert(1)</script>') is True
  ```

## Commands

| Command                | Purpose                                             |
|------------------------|-----------------------------------------------------|
| /update-ci-workflow    | Update or refactor GitHub Actions CI workflows      |
| /update-owasp-security | Implement or fix security features in OWASP module  |
```