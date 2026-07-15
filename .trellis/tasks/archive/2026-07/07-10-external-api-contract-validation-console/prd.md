# External API contract validation console

## Goal

Add an authenticated, secret-safe External API contract validation console for operators. The console should prove that the live local discovery contracts are internally consistent before an external service consumes them, without requiring a plaintext API key, making network calls, creating mailboxes, reading messages, or probing upstream providers.

## Background

- The project already exposes external discovery through `/api/v1/external/health`, `/capabilities`, `/integration-bundle`, `/providers`, `/mailboxes`, `/openapi.json`, and legacy `/api/external/*` aliases.
- `scripts/external_api_smoke.py` contains high-value read-only contract checks, but operators currently need to copy a shell command and supply an API key to run them.
- Settings -> API Security already has an External API command center with onboarding, smoke command copy, integration bundle launchpad, handoff kit, consumer usage, readiness, quickstart, session lifecycle, endpoint list, starter snippets, provider recipes, and workflow playbooks.
- This increment should add a local admin contract check to that existing command center, not a second product area.

## Requirements

- Add an authenticated admin endpoint at `/api/settings/external-api/contract-check`.
- The endpoint must return a local-only, read-only validation report for the external API discovery contract.
- The report must compose existing service-owned payloads instead of rebuilding provider selection, endpoint maps, OpenAPI metadata, integration bundle, or mailbox directory contracts in controllers or frontend code.
- The validation must cover health readiness, capabilities, integration bundle, provider discovery, mailbox directory sample, OpenAPI metadata, canonical v1 endpoint consistency, required workflows, action plan semantics, and placeholder command safety.
- The validation must not require or return plaintext external API keys, provider bearer tokens, passwords, JWTs, refresh tokens, task tokens, claim tokens, consumer keys, provider secret values, or Settings credential fields.
- The validation must not call upstream provider networks, claim pool inventory, create task temp mailboxes, read messages, mutate the database, or audit as an external API request.
- The Settings External API command center must render the validation result as an operational panel before generated quickstart/playbook surfaces, with loading, ready, warning/failing, and error states.
- The frontend must fetch only the admin endpoint and must not call `/api/v1/external/*` or read Settings secret inputs to compute validation status.
- The UI must stay consistent with the existing dense operational dashboard style and must not introduce a new frontend stack or third-party dependency.

## Acceptance Criteria

- [ ] `GET /api/settings/external-api/contract-check` requires login and returns `success: true` with a `contract_check` object.
- [ ] The `contract_check` object includes `status`, `summary`, `groups`, `generated_at`, `local_only`, `network_probes`, `mutation_safe`, and a bounded list of `next_actions`.
- [ ] Passing local contracts return `status=pass`; validation failures return `status=fail`; unexpected validation exceptions return `status=error` without leaking raw secrets.
- [ ] Check rows include stable `name`, `description`, `passed`, `group`, and `severity` fields suitable for UI rendering.
- [ ] The backend implementation preserves route -> controller -> service boundaries and module-boundary tests remain green.
- [ ] Settings UI adds contract-check state, fetch helper, renderer, event refresh hook, CSS hooks, and i18n labels.
- [ ] The contract-check UI does not reference Settings secret input IDs or built-in provider names inside validation helpers.
- [ ] Focused backend/API/frontend contract tests cover schema, auth, secret safety, render order, failure state, copy-independent behavior, and CSS hooks.
- [ ] `python scripts/project_readiness_check.py`, focused pytest suites, and `git diff --check` pass before commit.

## Notes

- UI brief: audience is operators and external-service integrators; primary workflow is "can I hand this API to another service now?"; product archetype is operational SaaS/admin; source of truth is existing provider catalog, integration bundle, OpenAPI, smoke validation, and Settings command-center styling; acceptance requires focused tests and rendered desktop/mobile QA because the settings command center changes pixels.
