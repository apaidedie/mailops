# External API smoke JSON report

## Goal

Make the external API smoke checker usable as a deployment/CI gate by adding machine-readable JSON output while preserving the current human-readable text output.

This directly supports the project's professional external integration goal: operators and downstream services should be able to verify health, discovery, provider readiness, OpenAPI, unified mailbox directory, and secret-safety contracts before connecting production workers.

## Confirmed Facts

- `scripts/external_api_smoke.py` already performs read-only checks against `/api/v1/external/health`, capabilities, providers, mailboxes, and OpenAPI.
- The checker currently returns exit `0` on success, `1` on contract failures, and `2` on smoke fetch/setup errors.
- Current output is line-oriented text (`OK ...` / `FAIL ...`), useful for humans but awkward for CI systems that need a summary object or failure list.
- `tests/test_external_api_smoke_script.py` already provides synthetic payloads plus a live Flask-test-client contract test.
- `docs/external-integration-quickstart.md` already recommends the smoke script as a deployment gate.

## Requirements

- Add `--format text|json` to `scripts/external_api_smoke.py`, defaulting to existing text output.
- JSON output must include:
  - `success`, `total`, `passed`, `failed`;
  - `checks` array with each check's `ok`, `name`, and `message`;
  - `failures` array containing only failed checks;
  - `endpoints` listing the canonical read-only paths the smoke checker calls.
- For smoke setup/fetch errors under `--format json`, print a JSON error object to stderr and keep exit code `2`.
- Preserve current exit code semantics for text and JSON modes.
- Keep the script read-only: do not add session start/read/close, provider network probes, pool claims, task-temp creation, or lifecycle mutation.
- Update quickstart docs with a CI-friendly JSON example.

## Acceptance Criteria

- [x] Existing text output behavior and exit codes remain compatible.
- [x] JSON success output is parseable and reports accurate totals and endpoints.
- [x] JSON failure output includes failed checks and exits `1`.
- [x] JSON smoke setup errors print parseable stderr JSON and exit `2`.
- [x] Tests cover JSON success, JSON contract failure, JSON smoke error, and default text output.
- [x] Quickstart docs show `--format json` usage for CI/deployment gating.
- [x] Existing live external discovery contract test still passes.
- [x] `git diff --check` reports no whitespace errors.

## Out of Scope

- No new backend routes or external API response changes.
- No mutating smoke checks.
- No provider-specific upstream network probing.
