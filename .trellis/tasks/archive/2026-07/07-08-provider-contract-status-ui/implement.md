# Provider Contract Status UI Implementation Plan

## Checklist

1. Inspect current settings provider UI mounts, provider catalog caching, plugin loading, and frontend contract tests.
2. Add focused failing frontend tests for the provider contract status mount, JS helpers, style hooks, provider-agnostic rendering, and secret-safety.
3. Add the template mount in the settings/provider area.
4. Add JavaScript state helpers and renderer that consume provider catalog and plugin contract summaries.
5. Add responsive CSS using existing operational settings styles.
6. Run targeted frontend/provider tests, `git diff --check`, and debug-log search.
7. Commit, archive task, and record journal.

## Validation Commands

```bash
python -m pytest tests/test_settings_tab_refactor_frontend.py tests/test_temp_mail_plugin_api.py tests/test_temp_mail_plugin_factory.py tests/test_multi_mailbox.py -q
python -m pytest tests/test_external_api.py tests/test_external_api_smoke_script.py -q
git diff --check
rg -n "console\.(log|debug)\(" static templates tests/test_settings_tab_refactor_frontend.py
```

If rendered browser checks are feasible in this repo state, run a desktop/mobile settings-page screenshot inspection before final reporting.

## Risk Points

- Do not duplicate provider validation logic in JavaScript.
- Do not expose raw validation payloads or secret-bearing config fields.
- Do not add provider-name conditionals.
- Keep layout responsive and compact inside the existing settings page.
