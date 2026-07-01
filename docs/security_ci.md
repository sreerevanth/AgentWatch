# Automated CI Code Quality and Security Guard (ELUSoC_2026)

## Overview
To maintain security compliance and avoid regression, the repository implements a PR linting workflow.

## Steps Performed
1. **Security Vulnerability Scan**: Invokes `Bandit` to inspect files for security issues.
2. **Coverage Gate**: Validates that test suites execute and code coverage remains above the minimum threshold (default: 70%).

## Files Involved
- `.github/workflows/coverage_security_guard.yml` - CI runner setup.
- `scripts/verify_coverage.py` - Coverage limit checker.
- `tests/test_coverage_guard.py` - Unit test verifying threshold limits.
