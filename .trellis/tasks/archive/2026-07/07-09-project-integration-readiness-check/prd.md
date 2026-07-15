# Project integration readiness check

## Goal

Add a local, read-only project readiness checker that helps maintain GitHub-ready quality for deployment, provider onboarding, and external API integration.

## User Value

Before publishing, deploying, or handing the project to another service, maintainers should be able to run one command and see whether the repository still contains the essential integration documents, env/config examples, external API clients, smoke checks, and secret-safe provider guidance.

## Confirmed Facts

The repository already has a live external API smoke checker for running instances, starter clients, provider onboarding docs, `.env.example`, provider config examples, OpenAPI/docs endpoints, and extensive provider selection contracts. There is no local repository-level readiness checker that verifies those assets stay present and consistent before a release. README and docs already describe the integration model, so this task should not duplicate that content; it should add a compact verification gate and document how to run it.

## Requirements

The checker must be local-only and read-only. It must not require a running server, API key, network access, provider secrets, mailbox sessions, or database mutation. It must verify the project contains the minimum assets needed for deployment and external integration: README links, external integration quickstart, provider onboarding guide, env example, provider JSON/TOML examples, Python/JavaScript starter clients, external API smoke checker, plugin template, and key test coverage. It must verify docs and examples reference canonical `/api/v1/external/*` endpoints, provider-neutral mailbox sessions, integration manifests, and placeholder auth. It must scan checked-in integration docs/examples/config templates for obvious secret values while allowing placeholder values and secret key names. It must support `--format text|json`, return exit code `0` when all checks pass and `1` when any readiness check fails, and produce stable JSON that can be used by CI.

## Acceptance Criteria

- [x] `scripts/project_readiness_check.py` exists, is zero third-party dependency, and supports text and JSON output.
- [x] The checker validates required repository assets, canonical external API references, provider onboarding/config examples, starter clients, smoke checker availability, and obvious secret-value leaks.
- [x] The checker is covered by tests for success, missing assets, JSON output, and secret leak detection.
- [x] README or external integration docs mention the local readiness checker as a release/deployment gate.
- [x] Existing external API smoke/client tests and new readiness checker tests pass.

## Out of Scope

This task does not call live external API endpoints, add provider-specific API implementations, mutate mailbox state, change provider selection semantics, or replace the existing live `external_api_smoke.py` checker.
