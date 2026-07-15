# Unified Mailbox Session Close API Implementation Plan

## Checklist

1. Add failing tests in `tests/test_external_mailbox_session_start_api.py` for unified close success and errors.
2. Extend OpenAPI/discovery assertions in existing external API tests for `mailbox_session_close`.
3. Add route registration for `/api/external/mailbox-sessions/close`.
4. Implement controller helper/handler in `outlook_web/controllers/external_temp_emails.py` by reusing pool and temp-mail services.
5. Update `outlook_web/services/provider_catalog.py` endpoint map, capabilities contract, quickstart request examples, and integration workflow steps.
6. Update `outlook_web/services/external_api_openapi.py` schemas and paths.
7. Update `docs/external-integration-quickstart.md` to show unified close.
8. Run targeted and full relevant regressions.
9. Update specs if the new session lifecycle contract should be preserved for future work.
10. Commit, archive task, and record journal.

## Validation Commands

```bash
python -m pytest tests/test_external_mailbox_session_start_api.py -q
python -m pytest tests/test_external_api.py tests/test_external_api_smoke_script.py -q
python -m pytest tests/test_external_pool.py tests/test_external_temp_emails_api.py -q
git diff --check
rg -n "console\.(log|debug)\(" static templates tests/test_settings_tab_refactor_frontend.py
```

## Risk Points

- Do not bypass existing pool access and public-mode restrictions for pool-backed closes.
- Do not allow a multi-key consumer to finish another consumer's task temp mailbox.
- Do not document secret-bearing lifecycle internals in OpenAPI or discovery payloads.
- Do not remove specialized endpoints.

## Rollback Points

The code path is additive. If tests expose broad incompatibility, revert route/controller/discovery/OpenAPI/docs changes and leave existing lifecycle endpoints untouched.
