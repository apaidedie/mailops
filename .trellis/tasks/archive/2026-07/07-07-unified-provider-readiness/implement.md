# Implementation Plan

## Steps

1. Add backend tests for `provider_context.readiness_summary` in admin and external mailbox directory payloads.
2. Add OpenAPI and frontend contract expectations for the new readiness summary field and renderer consumption.
3. Implement provider inventory summarization in `mailbox_catalog` and readiness projection in `provider_catalog`.
4. Update `external_api_openapi.py` schemas for the new summary contract.
5. Update `static/js/features/mailboxes.js`, `static/css/main.css`, and translations only as needed for the compact readiness display.
6. Run focused backend, external API, frontend contract, JS syntax, and whitespace checks.

## Validation Commands

```powershell
python -m pytest tests/test_unified_mailbox_catalog.py tests/test_external_temp_emails_api.py tests/test_external_api.py tests/test_unified_mailbox_frontend_contract.py -q -rs
node --check static/js/features/mailboxes.js
node --check static/js/i18n.js
git diff --check
```

## Rollback

Revert the readiness summary helper, the `provider_context` field addition, the UI render additions, and the OpenAPI schema update. Existing unified mailbox directory behavior should continue because this is an additive field.
