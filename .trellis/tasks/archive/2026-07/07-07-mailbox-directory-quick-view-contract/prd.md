# Mailbox directory quick-view contract

## Goal

Promote unified mailbox quick-view presets from a frontend-only convenience into the shared mailbox directory contract so admin UI clients and external projects can discover the same recommended aggregation workflows.

## Confirmed Facts

- `/api/mailboxes` and `/api/external/mailboxes` already share `get_mailbox_catalog_contract()` for filter values, definitions, and summary fields.
- `/api/external/capabilities` exposes `mailbox_directory.contract`, and `/api/external/openapi.json` exposes the mailbox directory schema.
- The current admin UI has frontend quick-view presets for all mailboxes, account mailboxes, temp mailboxes, readable mailboxes, and inactive items.
- The frontend presets are intentionally provider-agnostic and only use existing filter fields.

## Requirements

- Add quick-view preset metadata to the shared mailbox directory contract returned by backend discovery and directory APIs.
- Preset metadata must use only existing directory filter fields: `kind`, `status`, `read_capability`, `action`, `provider`, `sort`, and `search`.
- Preserve the existing API query contract and response shape compatibility. Adding `quick_view_presets` must not remove or rename existing fields.
- Make the admin UI consume contract-provided presets when available while keeping a safe fallback for older payloads.
- Keep presets provider-agnostic. Do not branch on `duckmail`, `mail_tm`, `emailnator`, `gptmail`, or any other provider key.
- Do not expose provider secret values, API keys, bearer tokens, passwords, JWTs, task tokens, refresh tokens, or consumer keys.
- Update OpenAPI/discovery schemas so external callers can generate clients that know about the preset contract.
- Keep frontend layout, manual filter behavior, stale-response guard, and quick-view custom state intact.

## Acceptance Criteria

- [x] `outlook_web/services/mailbox_directory_contract.py` exposes `quick_view_presets` with stable keys, labels, descriptions, and filter objects.
- [x] `/api/mailboxes`, `/api/external/mailboxes`, `/api/external/capabilities`, and `/api/external/openapi.json` include or describe the shared preset contract.
- [x] `static/js/features/mailboxes.js` prefers contract-provided presets and falls back to local presets only when the contract is absent.
- [x] Frontend and backend tests cover preset contract exposure, OpenAPI schema coverage, frontend contract consumption, provider-agnostic behavior, and secret-safety scans.
- [x] Existing unified mailbox list, provider facets, capability matrix, quick-view custom state, and stale-response guard still work.
- [x] `python -m pytest tests/test_unified_mailbox_catalog.py tests/test_external_api.py tests/test_external_temp_emails_api.py tests/test_unified_mailbox_frontend_contract.py -q` passes.
- [x] Syntax/static checks, debug-console scan, and DuckMail-token scan pass.

## Verification

- `node --check static/js/features/mailboxes.js`
- `python -m pytest tests/test_unified_mailbox_catalog.py tests/test_external_api.py tests/test_external_temp_emails_api.py tests/test_unified_mailbox_frontend_contract.py tests/test_multi_mailbox.py -q`
- `git diff --check`
- `rg -n "dk_[0-9a-fA-F]{20,}|DUCKMAIL_BEARER_TOKEN\s*=\s*dk_|Bearer\s+dk_" templates static tests .trellis docs README.md README.en.md .env.example docker-compose.yml outlook_web`
- `rg -n "console\.(log|debug)" static\js -g '!tests/layout-system/coverage/**'`

## Notes

- This is a contract alignment task, not a new provider implementation.
- Keep the task narrow enough to complete in one implementation pass while moving toward external-project usability.
