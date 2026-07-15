# External readiness API contract implementation plan

## Checklist

1. Add failing tests in tests/test_external_api.py for health readiness mailbox_directory inventory, multi-key allowed_emails scoping, secret-free projection, and OpenAPI schema requirements.
2. Run targeted tests and confirm they fail because readiness.mailbox_directory is missing.
3. Implement mailbox_directory projection in outlook_web.services.provider_catalog.get_external_api_readiness_summary, reusing outlook_web.services.mailbox_catalog.list_unified_mailboxes inside the function body to avoid module import cycles.
4. Add OpenAPI schema support for ExternalReadinessMailboxDirectory and require it from ExternalReadinessSummary.
5. Update .trellis/spec/backend/provider-selection-contract.md with the new health readiness field and test requirement.
6. Run focused and relevant regression checks.
7. Commit implementation, archive the Trellis task, and record the session journal.

## Validation Commands

- python -m pytest tests/test_external_api.py -q -rs
- python -m pytest tests/test_external_temp_emails_api.py tests/test_unified_mailbox_catalog.py -q -rs
- python -m py_compile outlook_web/services/provider_catalog.py outlook_web/services/external_api_openapi.py
- git diff --check
- git diff | Select-String -Pattern 'dk_[0-9a-fA-F]{20,}|DUCKMAIL_BEARER_TOKEN=|Bearer\s+[A-Za-z0-9_.-]+|X-API-Key:\s+(?!<your-api-key>)\S+' -CaseSensitive:$false

## Risk And Rollback

- Risk: provider_catalog imports mailbox_catalog at module import time, creating a cycle. Mitigation: perform the mailbox_catalog import inside the readiness helper only.
- Risk: health becomes too expensive. Mitigation: request page_size=1 and project summary/totals only.
- Rollback: remove the mailbox_directory field, OpenAPI schema addition, spec text, and tests from this task's diff.
