# CI readiness gate wiring

## Goal

Wire the local repository readiness checker into the existing GitHub Actions and release process so integration docs, provider onboarding assets, starter clients, and secret-safety checks are enforced automatically before pull requests and Docker publishing.

## User Value

Maintainers should not have to remember to run `scripts/project_readiness_check.py` manually before every release or external integration change. CI should catch missing integration assets, canonical endpoint drift, broken examples, and obvious checked-in provider/API secrets before those changes reach GitHub releases or Docker images.

## Confirmed Facts

The repository already has `.github/workflows/code-quality.yml`, `.github/workflows/python-tests.yml`, and `.github/workflows/docker-build-push.yml`. The Docker publish workflow already has a `quality-gate` job, while the new local checker is currently documented and tested but not enforced by CI. Existing workflows use path filters, so documentation and provider-template changes must be included explicitly where they should trigger readiness checks.

## Requirements

The implementation must reuse existing workflows rather than creating a duplicate CI stack. It must run `python scripts/project_readiness_check.py` in a GitHub Actions job that does not require network, API keys, provider secrets, a running server, or third-party Python dependencies. It must ensure integration docs/config/example changes trigger that gate on pull requests. It must also run the readiness checker in the Docker publish quality gate before image build/push. Release documentation and PR expectations must mention the gate. A local test must protect the workflow wiring so future edits do not silently remove the readiness gate or the relevant path filters.

## Acceptance Criteria

- [x] Existing GitHub Actions include a repository readiness gate that runs `python scripts/project_readiness_check.py`.
- [x] The readiness gate is triggered by changes to integration docs, provider onboarding docs, `.env.example`, provider config examples, starter clients, the smoke checker, the readiness checker, and its tests.
- [x] Docker publish quality gate runs the readiness checker before build/push.
- [x] Release docs or PR template mention the readiness gate as a required release/integration check.
- [x] Tests verify the workflow wiring and relevant validation commands pass locally.

## Out of Scope

This task does not change runtime API behavior, provider implementations, Docker image contents, secret storage, or GitHub repository settings/secrets. It does not push commits or create a pull request.
