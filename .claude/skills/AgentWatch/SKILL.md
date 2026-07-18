```markdown
# AgentWatch Development Patterns

> Auto-generated skill from repository analysis

## Overview
AgentWatch is a Python-based project focused on developing and evaluating benchmark suites for reasoning auditors. The repository emphasizes structured development patterns, clear coding conventions, and workflow automation to streamline the creation and iteration of benchmarks.

## Coding Conventions

- **File Naming:**  
  Use `snake_case` for all Python files and scripts.  
  *Example:*  
  ```
  generate_cases.py
  run_eval.py
  test_cases.json
  ```

- **Import Style:**  
  Use relative imports within the package.  
  *Example:*  
  ```python
  from .utils import load_cases
  ```

- **Export Style:**  
  Use named exports (explicitly define what is exported from modules).  
  *Example:*  
  ```python
  __all__ = ["generate_cases", "run_eval"]
  ```

- **Commit Messages:**  
  Follow [Conventional Commits](https://www.conventionalcommits.org/) with prefixes: `feat`, `fix`, `chore`.  
  *Example:*  
  ```
  feat: add new evaluation script for benchmarks
  fix: correct case generation logic
  chore: update benchmark documentation
  ```

## Workflows

### Benchmark Suite Development and Iteration
**Trigger:** When someone wants to create or update a benchmark suite for reasoning auditor.  
**Command:** `/new-benchmark-suite`

1. **Edit or Add Python Scripts:**  
   Update or create scripts for generating or running benchmarks, such as `generate_cases.py` or `run_eval.py`.
   ```python
   # Example: Adding a new benchmark case generator
   def generate_cases():
       # logic to generate test cases
       pass
   ```
2. **Update or Create Test Case Files:**  
   Modify or add new test cases in `test_cases.json`.
   ```json
   [
     {
       "id": "case_001",
       "input": "Sample input",
       "expected_output": "Expected result"
     }
   ]
   ```
3. **Update Benchmark Results:**  
   Save new evaluation results to `results/eval_latest.json`.
   ```json
   {
     "case_001": {
       "result": "pass",
       "score": 0.98
     }
   }
   ```
4. **Update Documentation:**  
   Document changes and usage in `benchmarks/README.md`.

## Testing Patterns

- **Framework:** Unknown (not explicitly detected).
- **File Pattern:** Test files are expected to match `*.test.ts`.  
  > *Note: While the codebase is Python, the test file pattern suggests possible TypeScript or external test scripts. Ensure Python tests are clearly named and documented if added.*

## Commands

| Command               | Purpose                                                        |
|-----------------------|----------------------------------------------------------------|
| /new-benchmark-suite  | Start or update a benchmark suite for reasoning auditor        |
```
