# Dependency security automation

## Goal

Add repository-level dependency security automation so Python packages and GitHub Actions are continuously updated and known-vulnerability checks block pull requests and release publishing. The solution should improve GitHub trust and release readiness without requiring provider credentials, a running server, or network access in the local readiness gate.

## Confirmed Facts

- The repository already has Python test, code-quality, Docker publish, release, and SonarQube workflows.
- Bandit scans project source code, but no workflow currently audits installed third-party Python dependencies.
- `.github/dependabot.yml` does not exist.
- `requirements.txt` uses compatible lower bounds rather than a lock file.
- A local `pip-audit 2.10.1` run against `requirements.txt` reports no known vulnerabilities.
- `scripts/project_readiness_check.py` is the repository's read-only local handoff gate and already validates required project assets without network or secrets.

## Requirements

- Add Dependabot configuration for both `pip` and `github-actions` ecosystems.
- Use a restrained weekly update cadence, bounded open pull requests, predictable labels, and grouped non-major dependency updates to reduce maintenance noise.
- Add a dedicated dependency-security workflow that runs on relevant pushes and pull requests, weekly schedule, and manual dispatch.
- Pin the audit tool version used by CI so scanner behavior is reviewable and reproducible.
- Produce an uploadable JSON audit report even when vulnerabilities are found, then fail the job using the captured audit exit code.
- Keep workflow permissions read-only except for artifact upload capabilities provided by GitHub Actions.
- Add the same dependency vulnerability gate to the Docker release quality job before tests and image publication.
- Extend the local project readiness checker with a static, network-free contract check for Dependabot and dependency-audit workflow wiring.
- Add focused tests covering workflow triggers, scanner pinning, report upload/failure behavior, Dependabot ecosystems and cadence, release gating, and readiness integration.
- Mark the dependency scanning item complete in `docs/项目地图.md` once verification passes.

## Acceptance Criteria

- [x] `.github/dependabot.yml` configures weekly `pip` and `github-actions` updates with bounded PR limits and grouped non-major updates.
- [x] `.github/workflows/dependency-security.yml` audits `requirements.txt` with pinned `pip-audit==2.10.1` on push, pull request, weekly schedule, and manual dispatch.
- [x] The dependency-security workflow uploads `pip-audit-report.json` with `if: always()` and fails when the captured audit exit code is non-zero.
- [x] `.github/workflows/docker-build-push.yml` runs the pinned dependency audit in `quality-gate` before repository readiness and tests.
- [x] `scripts/project_readiness_check.py` reports a dedicated dependency-security automation result without network access.
- [x] Focused workflow/readiness tests pass.
- [x] A real local `pip-audit` run against `requirements.txt` passes.
- [x] `python scripts/project_readiness_check.py`, relevant test suites, and `git diff --check` pass.

## Out Of Scope

- Introducing a dependency lock file or changing current package version ranges.
- Automatically merging Dependabot pull requests.
- Container image CVE scanning; that remains a separate project-map item.
- Suppressing or ignoring known vulnerabilities without a documented project-specific exception process.
