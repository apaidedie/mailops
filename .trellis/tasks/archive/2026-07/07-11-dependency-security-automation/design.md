# Design

## Architecture

Use GitHub-native automation plus the PyPA `pip-audit` CLI. A dedicated workflow owns scheduled and change-triggered dependency audits, while the Docker publish workflow repeats the same pinned audit as a release-blocking gate. Dependabot owns update discovery for Python requirements and GitHub Actions.

The local readiness checker performs static contract validation only. It verifies that the expected files and critical workflow tokens are present; it never installs packages, calls PyPI, resolves dependencies, or depends on GitHub state.

## Workflow Contracts

- Scanner: `pip-audit==2.10.1`.
- Input: `requirements.txt`.
- Report: `pip-audit-report.json` using JSON format.
- Failure: capture the scanner exit code, upload the report with `if: always()`, then fail explicitly when the exit code is non-zero.
- Dedicated workflow triggers: relevant push and pull request paths, weekly cron, and `workflow_dispatch`.
- Dependabot ecosystems: `pip` at `/` and `github-actions` at `/`, weekly cadence.

## Compatibility

Do not modify application dependencies or runtime startup. Existing Bandit, tests, readiness checks, Docker build/push behavior, and branch/tag triggers remain intact. The Docker quality gate gains an earlier dependency audit step but retains its current build ordering after the gate succeeds.

## Security And Operations

Use `permissions: contents: read` in the dedicated workflow. Do not inject provider secrets or external API keys. Audit output is a CI artifact and may contain package names, versions, vulnerability identifiers, and fix versions, but no project credentials.

Dependabot groups patch and minor updates to reduce PR volume while leaving major updates isolated for explicit review. Open PR limits prevent automation noise from crowding out project work.

## Rollback

If the dedicated workflow causes platform-specific failures, remove only that workflow while retaining Dependabot and the Docker release audit. If a scanner release regresses, update the single pinned version consistently in the dedicated workflow, Docker workflow, readiness contract, and tests.
