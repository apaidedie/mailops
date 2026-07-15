# Provider readiness preflight contract implementation plan

## Steps

- [x] Add failing tests for admin preflight, external preflight, no-network default, explicit probe, OpenAPI path, discovery endpoint propagation, and secret redaction.
- [x] Add `PROVIDER_PREFLIGHT_ENDPOINT` and endpoint-map support in `provider_catalog`.
- [x] Implement `get_mailbox_provider_preflight(probe_network=False)` by composing provider diagnostics, selection policy, integration guide, readiness summary, and `get_mailbox_provider_health` rows.
- [x] Add admin and external controllers and routes.
- [x] Add capabilities/provider discovery/manifest/quickstart/OpenAPI exposure.
- [x] Run focused tests, inspect diff, update specs only if a new durable convention appears, then commit and archive the task.

## Validation

Run `python -m pytest tests/test_external_temp_emails_api.py tests/test_multi_mailbox.py tests/test_external_api.py -q` if the focused subset remains practical. At minimum run the exact new/affected tests plus `python -m pytest tests/test_unified_mailbox_catalog.py tests/test_unified_mailbox_frontend_contract.py -q` if provider context discovery changes affect unified mailbox contracts.

## Rollback

All changes are additive. Roll back route registration, controller handlers, provider catalog helper/endpoint map edits, OpenAPI path/schema additions, and focused tests together if the contract proves wrong.
