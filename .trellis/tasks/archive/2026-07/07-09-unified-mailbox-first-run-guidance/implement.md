# Unified mailbox first-run guidance implementation plan

## Checklist

1. Read relevant frontend/backend specs and current unified mailbox files.
2. Add the template mount point and static loading shell.
3. Add i18n keys for the setup panel and action labels.
4. Implement a provider-agnostic setup model + renderer in `static/js/features/mailboxes.js`.
5. Add responsive CSS hooks in `static/css/main.css`.
6. Extend frontend contract tests for DOM, JS, CSS, i18n, provider-agnostic, and secret-safety behavior.
7. Run focused tests and syntax checks.
8. Run the project readiness checker.
9. Start the app and run a desktop/mobile rendered check for the unified mailbox page.
10. Commit, archive the Trellis task, and record journal progress.

## Validation Commands

```powershell
python -m pytest tests\test_unified_mailbox_frontend_contract.py tests\test_unified_mailbox_catalog.py -q
node --check static\js\features\mailboxes.js
node --check static\js\main.js
node --check static\js\i18n.js
python scripts\project_readiness_check.py
git diff --check
```

## Rollback Point

- If the setup renderer creates unstable assumptions about `/api/mailboxes`, revert only the new mount point, renderer, CSS, and tests for this task. Do not touch earlier provider or external API work.
