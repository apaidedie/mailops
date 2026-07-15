# External provider integration guide

## Goal

Make the external API discovery payload tell callers exactly how to choose and configure mailbox providers without reverse-engineering `deployment_profile`, `selection_policy`, and provider catalog fields.

## Requirements

- `/api/external/capabilities`, `/api/external/providers`, and embedded mailbox `provider_context` must expose a secret-free `provider_integration_guide` object.
- The guide must be data-driven from the existing provider catalog, deployment profile, selection policy, active allowlist, diagnostics, and endpoint map.
- For each provider, the guide must describe the provider key, label, kind, active/readiness status, required/optional env keys, required settings keys, activation env/config examples, default-selection env/config examples, per-request field names, and relevant discovery/read endpoints.
- The guide must preserve alias compatibility for existing GPTMail/legacy bridge values and account-level `imap` allowlist behavior.
- The guide must not expose credential values, bearer tokens, API keys, passwords, JWTs, task tokens, consumer keys, or raw secret settings.
- OpenAPI schemas and tests must document and protect the new discovery field.
- Existing provider selection, health, mailbox catalog, and external API behavior must remain backward compatible.

## Acceptance Criteria

- [x] A shared service helper returns a `provider_integration_guide` with versioned top-level metadata, workflow instructions, alias maps, and per-provider entries.
- [x] `/api/external/capabilities` includes the guide at top level.
- [x] `/api/external/providers` includes the same guide alongside the provider catalog.
- [x] `provider_context` inside unified mailbox directory responses includes the same guide.
- [x] OpenAPI exposes `provider_integration_guide` for capabilities and mailbox provider context schemas.
- [x] Tests cover guide shape, provider-specific examples, alias preservation, and secret-free output.
- [x] Relevant external API/provider/unified mailbox tests pass.

## Verification

- `python -m pytest tests/test_external_api.py tests/test_external_temp_emails_api.py tests/test_unified_mailbox_catalog.py tests/test_multi_mailbox.py -q` -> 184 passed, 5 subtests passed.
- `python -m compileall -q outlook_web` -> passed.
- `git diff --check` -> passed.
- `python -m pytest -q` -> 1685 passed, 14 skipped, 34 subtests passed.

## Notes

This is a backend discovery contract improvement. UI rendering is intentionally out of scope for this increment.
