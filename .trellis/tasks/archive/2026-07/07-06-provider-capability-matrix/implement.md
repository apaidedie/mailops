# Provider capability matrix implementation plan

## Checklist

- Read the current unified mailbox template, `static/js/features/mailboxes.js`, unified mailbox CSS, `static/js/i18n.js`, and frontend contract tests immediately before editing.
- Add `#unifiedProviderCapabilityMatrix` to `templates/index.html` inside `mailboxUnifiedLayout`, after `#unifiedMailboxProviderContext` and before `#unifiedMailboxList`.
- Add `renderUnifiedProviderCapabilityMatrix(providerContext, contract, state, selectedProvider)` in `static/js/features/mailboxes.js`.
- In loading and error states, call the matrix renderer with empty context and matching state.
- In the successful `loadUnifiedMailboxes()` path, call the matrix renderer with `data.provider_context`, `data.contract`, state `ready`, and the normalized selected provider.
- Build provider rows from `provider_context.provider_integration_guide.providers`, with defensive fallbacks for missing arrays or malformed entries.
- Reuse `setUnifiedProviderFilter()` through event delegation only if row filter affordances are added.
- Add CSS selectors under the unified mailbox directory section and mobile rules under the existing max-width block.
- Add i18n entries for new visible labels.
- Extend `tests/test_unified_mailbox_frontend_contract.py` for the mount, JS renderer, render calls, CSS hooks, i18n strings, and absence of local provider behavior branches in the new renderer.

## Validation Commands

Run these before completion:

```bash
node --check static/js/features/mailboxes.js
node --check static/js/i18n.js
git diff --check
rg -n "console\.(log|debug)" static\js -g '!tests/layout-system/coverage/**'
rg -n "dk_[0-9a-fA-F]{20,}|DUCKMAIL_BEARER_TOKEN\s*=\s*dk_|Bearer\s+dk_" templates static tests .trellis docs README.md README.en.md .env.example docker-compose.yml outlook_web
python -m pytest tests/test_unified_mailbox_frontend_contract.py tests/test_unified_mailbox_catalog.py -q
python -m pytest tests/test_external_api.py tests/test_external_api_temp_mail_compat.py tests/test_external_temp_emails_api.py tests/test_temp_mail_provider_public.py tests/test_temp_mail_settings_platform_contract.py -q
```

If CSS or layout density changes materially, start the Flask app and take Playwright screenshots for desktop and mobile unified mailbox views to check wrapping and horizontal overflow.

## Risk Points

- Do not consume `provider_context.provider_diagnostics.providers` as the primary row list; that can fight the directory provider-context spec.
- Do not add provider-specific key checks in frontend code.
- Do not add copy helpers that could accidentally include secret values.
- Keep old provider aliases visible through backend guide data.
- Keep the matrix compact enough that it does not push the mailbox list too far down on normal desktop viewports.

## Commit Shape

Commit the implementation separately from Trellis archive and journal commits. Suggested work commit message: `feat(frontend): add provider capability matrix`.
