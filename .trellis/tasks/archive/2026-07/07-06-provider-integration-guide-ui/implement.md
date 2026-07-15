# Provider integration guide UI implementation

## Checklist

- Add the guide mount to the settings provider area near existing templates and console.
- Add JavaScript cache state for `provider_integration_guide`, guide filter state, rendering helpers, and a provider-specific copy action.
- Add CSS for the guide header, summary, filter pills, provider rows, key chips, call examples, copy buttons, and mobile stacking.
- Extend frontend contract tests for DOM, JS, styles, translations, and secret-token non-exposure.
- Run targeted tests, then broader provider/API regressions if targeted changes pass.

## Validation Commands

```powershell
$env:PYTHONIOENCODING='utf-8'; python -m pytest tests/test_settings_tab_refactor_frontend.py tests/test_multi_mailbox.py tests/test_external_temp_emails_api.py tests/test_external_api.py tests/test_unified_mailbox_catalog.py -q
```

If browser startup is available without disruptive setup, also run a rendered settings-page check at desktop and mobile widths.

## Risk Notes

The highest risk is leaking a secret value through a copy helper or rendering a stale backend field as trusted UI text. Treat env defaults for keys in `secret_env` as empty and escape all rendered text.

The second risk is duplicating backend provider semantics in JavaScript. Keep JavaScript limited to display formatting and snippet assembly from guide fields.
