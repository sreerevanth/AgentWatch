# AgentWatch Engineering Audit

Audit date: 2026-07-12

Scope reviewed: Python package, frontend dashboard, landing page, documentation, Docker assets, GitHub Actions, tests, packaging metadata, and generated/local artifacts present in the repository workspace.

## Architecture

### Issue 1: Three independent applications share one repository root

- Severity: Medium
- Location: `agentwatch/`, `frontend/`, `agentwatch-landing/`
- Description: The repository contains a Python package, a Next.js 14 dashboard, and a Next.js 16 landing page with independent dependency graphs and runtime conventions.
- Why it matters: Contributors can accidentally mix dependencies, Dockerfiles, or components across apps, especially because both frontend apps use similar framework names but incompatible major versions.
- Recommended fix: Keep project-local config and Docker assets inside each app, document boundaries in onboarding docs, and avoid shared frontend source unless a deliberate package boundary is introduced.

### Issue 2: Public package exports depend on wildcard re-exports

- Severity: Low
- Location: `agentwatch/**/__init__.py`
- Description: Package entrypoints intentionally use wildcard re-exports.
- Why it matters: Wildcard exports make public API ownership harder to audit and can obscure unused imports.
- Recommended fix: Keep current behavior for compatibility, but define explicit `__all__` lists over time for stable public modules.

## Technical Debt

### Issue 3: Large CLI module has too many responsibilities

- Severity: Medium
- Location: `agentwatch/cli/main.py`
- Description: The CLI contains command routing, rendering, API calls, upgrade/checkout logic, policy display, server startup, export, compare, and live watch behavior in a single large module.
- Why it matters: Large command modules are hard to test in isolation and make small CLI changes risky.
- Recommended fix: Split by command family behind the existing Typer command surface without changing CLI behavior.

### Issue 4: Optional telemetry behavior was not reflected consistently in tests

- Severity: Medium
- Location: `tests/test_telemetry.py`
- Description: Several reasoning trace tests assumed OpenTelemetry was available even when the package correctly degrades without the optional OTel dependency.
- Why it matters: Environments without optional telemetry dependencies fail tests even though runtime behavior is intentionally optional.
- Recommended fix: Guard OTel-specific tests with the same `_OTEL_AVAILABLE` skip condition used elsewhere. Fixed in this pass.

## Duplicate Code

### Issue 5: Duplicate dashboard Dockerfiles

- Severity: Medium
- Location: `Dockerfile.frontend`, `frontend/Dockerfile`, `docker-compose.yml`
- Description: Two Dockerfiles built the same dashboard app, but CI used `frontend/Dockerfile` while Compose used the root `Dockerfile.frontend`.
- Why it matters: Duplicate build definitions drift and cause environment-specific production bugs.
- Recommended fix: Standardize on the app-local `frontend/Dockerfile` and update Compose to use it. Fixed in this pass; root duplicate removed.

## Dead Code

### Issue 6: One-off issue resolution note in docs

- Severity: Low
- Location: `docs/issue-498-resolved.md`
- Description: The file documented a closed issue/PR relationship rather than durable product or developer guidance.
- Why it matters: Stale project-management notes clutter published documentation and confuse contributors.
- Recommended fix: Keep issue history in GitHub and remove the note from docs. Fixed in this pass.

## Unused Files

### Issue 7: Generated Python bytecode and tool caches were present in the workspace

- Severity: Low
- Location: `agentwatch/**/__pycache__/`, `tests/__pycache__/`, `.ruff_cache/`, `pytest-cache-files-*`
- Description: Generated caches were present under the repository tree, and several were permission-restricted.
- Why it matters: Generated artifacts slow audits, pollute searches, and can break traversal on Windows.
- Recommended fix: Keep these ignored and remove them after validation runs. Cleaned during this pass; validation tools recreated some caches locally.

### Issue 8: Coverage artifact deletion was already pending

- Severity: Low
- Location: `.coverage`
- Description: `.coverage` was already deleted in the working tree before this cleanup started.
- Why it matters: Coverage outputs should not be source-controlled.
- Recommended fix: Keep coverage artifacts ignored and do not commit regenerated coverage files.

### Issue 9: Root `__main__.py` deletion was already pending

- Severity: Low
- Location: `__main__.py`
- Description: A root-level `__main__.py` was already deleted before this cleanup started.
- Why it matters: A root entrypoint outside the installed package is ambiguous when `agentwatch/__main__.py` exists.
- Recommended fix: Keep the package entrypoint and avoid root-level executable shims unless they are documented and tested.

## Legacy Code

### Issue 10: Historical labels remained in documentation headings

- Severity: Low
- Location: `docs/architecture-detailed.md`, `docs/custom-adapters-tutorial.md`, `docs/developer-setup.md`, `docs/getting-started-extended.md`
- Description: Several docs included stale event/project suffixes in headings.
- Why it matters: Historical labels make current docs look forked or stale.
- Recommended fix: Use neutral durable document titles. Fixed before/within this cleanup set.

## Naming Problems

### Issue 11: Mixed getting-started filename styles

- Severity: Low
- Location: `docs/getting-started.md`, `docs/getting-started-extended.md`, `docs/cli/getting-started.md`
- Description: Documentation filenames mix kebab-case and snake_case.
- Why it matters: Inconsistent naming makes docs harder to discover and link.
- Recommended fix: Prefer kebab-case for docs pages in a future compatibility-preserving docs rename pass with redirects or link updates.

## Folder Structure

### Issue 12: Build output was not ignored

- Severity: Medium
- Location: `site/`, `.gitignore`
- Description: Running `mkdocs build` generates a root `site/` directory that was not ignored.
- Why it matters: Generated docs output can be accidentally committed.
- Recommended fix: Add `site/` to `.gitignore`. Fixed in this pass.

## API Consistency

### Issue 13: API response conventions are not centrally documented

- Severity: Low
- Location: `agentwatch/api/server.py`, `docs/api-reference.md`
- Description: API routes exist across safety, sessions, policies, telemetry, compliance, and security, but response envelope conventions are not documented in one place.
- Why it matters: Contributors may add inconsistent response shapes.
- Recommended fix: Add a contributor-facing API style section documenting existing conventions before accepting new API work.

## Documentation

### Issue 14: Durable docs existed outside MkDocs navigation

- Severity: Medium
- Location: `mkdocs.yml`, `docs/api-reference.md`, `docs/architecture-detailed.md`, `docs/custom-adapters-tutorial.md`, `docs/developer-setup.md`, `docs/getting-started-extended.md`
- Description: MkDocs built successfully but reported several durable docs pages that were not included in nav.
- Why it matters: Unlisted docs are effectively hidden from published documentation.
- Recommended fix: Add durable pages to MkDocs nav and remove stale notes. Fixed in this pass.

### Issue 15: Documentation had stale absolute local links

- Severity: Medium
- Location: `docs/architecture.md`
- Description: Architecture docs previously referenced local `file:///` paths from another machine.
- Why it matters: Absolute local links break for every contributor and in published docs.
- Recommended fix: Use relative links. Fixed before/within this cleanup set.

### Issue 16: README and package metadata version references must stay synchronized

- Severity: Low
- Location: `README.md`, `pyproject.toml`, `agentwatch/cli/demo.py`
- Description: Version and Python support references were being updated across multiple files.
- Why it matters: Drift between package metadata, badges, and CLI output undermines release trust.
- Recommended fix: Keep version bumps atomic and consider a small release checklist that lists all version-bearing files.

## Testing

### Issue 17: Full test suite is sensitive to local Windows temp permissions

- Severity: Medium
- Location: `tests/`, local temp path `C:\Users\sreer_mg\AppData\Local\Temp\pytest-of-sreer_mg`
- Description: Many tests using pytest temp fixtures failed locally because pytest could not access its temp root.
- Why it matters: Contributors on Windows can see unrelated fixture setup errors even when code is correct.
- Recommended fix: Document setting a writable temp directory for Windows test runs or configure CI/dev scripts to use a repo-local temp root.

### Issue 18: Tests ran under Python 3.14 despite project targeting Python 3.12

- Severity: Medium
- Location: Local validation environment, `pyproject.toml`
- Description: Local pytest used Python 3.14.2 while the project requires and CI targets Python 3.12.
- Why it matters: Python 3.14 can surface unrelated deprecations or dependency compatibility behavior not representative of CI.
- Recommended fix: Use a Python 3.12 virtual environment for official validation and document this explicitly in developer setup.

### Issue 19: Sentence-transformers mock is critical test infrastructure

- Severity: High
- Location: `tests/conftest.py`
- Description: Tests rely on a mock to avoid model downloads and hangs.
- Why it matters: Removing or weakening the mock makes test runs slow and network-dependent.
- Recommended fix: Keep the mock in `conftest.py` and add comments explaining why it exists. Existing behavior preserved.

## CI/CD

### Issue 20: CI security audit command used a missing tool and shell-specific process substitution

- Severity: High
- Location: `.github/workflows/ci.yml`
- Description: The security job attempted `pip-audit --requirement <(pip-compile pyproject.toml ...)` without installing `pip-compile`.
- Why it matters: The job can silently audit an empty requirement stream or behave differently by shell.
- Recommended fix: Install the package and run `pip-audit --desc` directly. Fixed in this pass.

### Issue 21: PR workflow intentionally does not hard-fail lint

- Severity: Low
- Location: `.github/workflows/test-on-pr.yml`
- Description: Ruff runs with `continue-on-error: true`; pytest is the hard gate.
- Why it matters: This is documented, but contributors may assume lint failures block merges.
- Recommended fix: Keep behavior if intentional; otherwise make lint a required check after the backlog is clean.

## Security

### Issue 22: Security baseline is large and should be periodically reviewed

- Severity: Medium
- Location: `bandit-baseline.json`, `.github/workflows/bandit.yml`
- Description: Bandit runs with a committed baseline.
- Why it matters: Baselines can hide real regressions if not reviewed and refreshed deliberately.
- Recommended fix: Add a scheduled baseline review process and require justification for new baseline entries.

### Issue 23: Docker API image runs as root

- Severity: Medium
- Location: `Dockerfile.api`
- Description: The API image uses `python:3.12-slim` without creating a non-root runtime user.
- Why it matters: Running as root increases container escape blast radius.
- Recommended fix: Add a non-root user and adjust ownership in a focused Docker hardening pass.

## Packaging

### Issue 24: `typer[all]` extra is obsolete with current Typer

- Severity: Medium
- Location: `pyproject.toml`
- Description: Installing the project reported that Typer no longer provides the `all` extra.
- Why it matters: Obsolete extras create install warnings and reduce trust in packaging metadata.
- Recommended fix: Replace `typer[all]` with explicit dependencies actually needed by the CLI, such as `typer`, `rich`, and `shellingham` if required.

### Issue 25: Docs install caused local dependency resolver conflict

- Severity: Medium
- Location: `pyproject.toml`, local Python environment
- Description: Installing `.[docs]` pulled `python-dotenv==1.0.1` through `litellm`, conflicting with another installed package requiring `python-dotenv>=1.1.0`.
- Why it matters: Broad unpinned dependencies can make editable installs unstable in shared environments.
- Recommended fix: Validate package extras in isolated Python 3.12 environments and consider dependency upper/lower-bound review.

## Performance

### Issue 26: Repository traversal was slowed by generated dependency/build artifacts

- Severity: Low
- Location: `node_modules/`, `.next/`, `.ruff_cache/`, `site/`, `pytest-cache-files-*`
- Description: Generated artifacts significantly increase scan volume when present.
- Why it matters: Large generated trees slow audits, grep, and contributor tooling.
- Recommended fix: Keep generated outputs ignored and avoid running audits without excluding dependency/build directories.

## Dependencies

### Issue 27: Dashboard dependencies include deprecated or vulnerable packages

- Severity: High
- Location: `frontend/package.json`, `frontend/package-lock.json`
- Description: `npm ci` warnings reported deprecated packages and a security warning for `next@14.2.30`.
- Why it matters: Frontend dependency drift can introduce security exposure.
- Recommended fix: Run a dedicated dashboard dependency update pass, staying within Next.js 14 unless deliberately upgrading the app.

### Issue 28: Landing dependency installation was not validated

- Severity: Medium
- Location: `agentwatch-landing/package.json`, `agentwatch-landing/package-lock.json`
- Description: Landing `npm ci` was not completed because dependency installation approval was interrupted and the sandbox cache lacked tarballs.
- Why it matters: Next.js 16 app validity cannot be confirmed without lockfile install and build.
- Recommended fix: Re-run `npm ci && npm run build` in `agentwatch-landing/` with network access in a clean workspace.

## Build System

### Issue 29: API Docker context lacked root `.dockerignore`

- Severity: Medium
- Location: `.dockerignore`, `Dockerfile.api`
- Description: API Docker builds copied the whole repository context without a root Docker ignore file.
- Why it matters: Build contexts can include caches, node modules, docs output, coverage, and local env files.
- Recommended fix: Add a root `.dockerignore`. Fixed in this pass.

## Type Safety

### Issue 30: Frontend type-check could not be validated locally

- Severity: Medium
- Location: `frontend/`
- Description: `npm run type-check` failed because `tsc` was unavailable after `npm ci` could not complete.
- Why it matters: Dashboard type safety remains unverified in this cleanup run.
- Recommended fix: Complete `npm ci` from `frontend/package-lock.json`, then run `npm run type-check`.

## Logging

### Issue 31: CLI and demo use direct terminal printing extensively

- Severity: Low
- Location: `agentwatch/cli/main.py`, `agentwatch/cli/demo.py`, `agentwatch/core/safety.py`
- Description: CLI paths intentionally use Rich/print output while library modules use logging.
- Why it matters: The boundary is acceptable, but direct prints in non-CLI library paths can complicate automation.
- Recommended fix: Keep interactive CLI output in CLI modules; evaluate library print paths for conversion to callbacks or logger-based output.

## Error Handling

### Issue 32: Local tool cache permission errors affect validation repeatability

- Severity: Low
- Location: `.ruff_cache/`, `.pytest_cache/`, `pytest-cache-files-*`
- Description: Ruff and pytest emitted permission warnings when writing caches.
- Why it matters: Cache failures create noisy validation logs and can leave undeletable generated folders.
- Recommended fix: Run validation with `ruff --no-cache` in constrained workspaces and configure pytest cache/temp paths to writable locations.

## Config

### Issue 33: Environment variable names differ between Docker and frontend config

- Severity: Low
- Location: `docker-compose.yml`, `frontend/pages/api/v1/[...path].ts`, `frontend/next.config.js`
- Description: Compose sets both `AGENTWATCH_API_URL` and `NEXT_PUBLIC_API_URL`; frontend runtime proxy behavior depends on server-side env.
- Why it matters: Contributors may set the wrong variable when debugging frontend API proxying.
- Recommended fix: Document frontend runtime and build-time environment variables in one dashboard setup section.

## Repository Hygiene

### Issue 34: `VISION.md` is untracked

- Severity: Medium
- Location: `VISION.md`
- Description: `VISION.md` exists in the workspace but is not tracked.
- Why it matters: Product vision docs should be versioned if they are authoritative; otherwise they should not live in the repo root.
- Recommended fix: Decide whether to commit it as canonical vision documentation or remove it from the workspace.

### Issue 35: Working tree was dirty before cleanup

- Severity: Medium
- Location: Multiple files
- Description: Several docs, benchmarks, tests, version metadata, `.coverage`, and root `__main__.py` were already modified/deleted before this pass.
- Why it matters: Broad cleanup work is harder to review when mixed with pre-existing changes.
- Recommended fix: Split commits by intent: pre-existing version/doc updates, cleanup changes, test hygiene, and generated artifact removal.

### Issue 36: Line-ending churn warnings appear on Windows

- Severity: Low
- Location: Multiple text files
- Description: Git warned that LF will be replaced by CRLF the next time Git touches several files.
- Why it matters: Uncontrolled line-ending churn creates noisy diffs.
- Recommended fix: Add or verify `.gitattributes` with normalized text handling.
