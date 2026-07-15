# Provider Diagnostics and Routing Hardening Implementation Plan

## Steps

1. Add backend contract tests for readiness summary `routing_matrix` on `/api/providers`, `/api/mailboxes`, and OpenAPI.
2. Add frontend contract expectations for `readinessSummary.routing_matrix` consumption in `static/js/features/mailboxes.js`.
3. Implement routing-matrix helpers in `outlook_web.services.provider_catalog` and include the matrix in `get_mailbox_provider_readiness_summary()`.
4. Update OpenAPI schemas for `MailboxProviderReadinessSummary` and routing-matrix provider rows.
5. Render a compact provider-routing strip in the unified mailbox provider readiness band without provider-specific branches.
6. Run targeted tests, then scoped browser-extension tests to confirm no unrelated regression.

## Validation Commands

- `python -m pytest tests/test_multi_mailbox.py tests/test_unified_mailbox_catalog.py tests/test_external_temp_emails_api.py tests/test_unified_mailbox_frontend_contract.py -q`
- `python -m pytest tests/test_smoke_contract.py -q`
- `npm run test:browser-extension`

## Risk Notes

The main risk is duplicating provider-selection logic. Implementation must derive every scope from `selection_policy.scopes` and provider rows from the guide/diagnostics projections.
