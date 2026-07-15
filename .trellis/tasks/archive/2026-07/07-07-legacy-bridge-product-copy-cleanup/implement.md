# Implementation Plan

## Steps

1. Read backend provider-selection and frontend provider UI specs before editing.
2. Update the single label owner in `provider_catalog` for the legacy bridge family.
3. Update settings/provider tests that assert the formal label, while preserving alias and migration assertions.
4. Update README, README.en, and `.env.example` copy around `GPTMAIL_*`, `legacy_bridge`, and active provider examples.
5. Run focused settings/provider/API tests, static checks, secret scan, and full regression if feasible.
6. Commit, archive the child task, and record the session journal.

## Guardrails

- Do not rename `GPTMAIL_BASE_URL`, `GPTMAIL_API_KEY`, `legacy_bridge`, `custom_domain_temp_mail`, `gptmail`, `legacy_gptmail`, or `temp_mail`.
- Do not remove alias maps or migration logic.
- Do not add provider-specific frontend branching.
- Do not write real provider secret values into docs, tests, or logs.

## Checks

- `python -m pytest tests/test_temp_mail_settings_platform_contract.py tests/test_temp_mail_target_contract.py tests/test_unified_mailbox_catalog.py tests/test_external_api.py -q -rs`
- `python -m pytest tests/test_unified_mailbox_frontend_contract.py -q -rs`
- `rg -n "dk_[0-9a-fA-F]{20,}|DUCKMAIL_BEARER_TOKEN\\s*=\\s*dk_|Bearer\\s+dk_" templates static tests .trellis docs README.md README.en.md .env.example docker-compose.yml outlook_web`
- `git diff --check`
- Full `python -m pytest -q -rs` when the focused suite is green.
