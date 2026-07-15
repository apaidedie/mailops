# Implementation Plan

## Steps

1. Add focused failing tests for Dependabot, dependency-security workflow, Docker release audit ordering, and readiness integration.
2. Add `.github/dependabot.yml` with weekly `pip` and `github-actions` policies.
3. Add `.github/workflows/dependency-security.yml` with pinned audit, JSON artifact upload, explicit failure gate, schedule, and path triggers.
4. Add the pinned audit step to the Docker `quality-gate` before readiness and tests.
5. Extend `scripts/project_readiness_check.py` with a static dependency-security automation check and update its tests.
6. Mark automatic dependency vulnerability scanning complete in `docs/项目地图.md`.
7. Run focused tests, local `pip-audit`, readiness gate, YAML parsing/static checks, and `git diff --check`.

## Validation Commands

`python -m unittest tests.test_dependency_security_automation tests.test_ci_readiness_gate_workflows tests.test_project_readiness_check -v`

`uvx --from pip-audit==2.10.1 pip-audit -r requirements.txt --progress-spinner off`

`python scripts/project_readiness_check.py`

`git diff --check`

## Risk And Rollback Points

- YAML quoting and GitHub expression syntax must remain valid; tests should parse or assert stable workflow structure before commit.
- The audit report step must not swallow vulnerability failures; verify explicit captured-status failure behavior.
- The local readiness gate must stay network-free and deterministic.
- Keep the scanner version synchronized across workflows, readiness checks, and tests.
