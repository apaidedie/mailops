# External provider recipe guide implementation

## Steps

1. Add frontend recipe helpers in `static/js/main.js` near the existing external integration manifest helpers.
2. Render the guide from `renderExternalApiCommandCenter()` and wire recipe selection/copy event delegation.
3. Add responsive styles in `static/css/main.css` beside existing external API starter/workflow styles.
4. Extend `tests/test_settings_tab_refactor_frontend.py` for helper, wiring, CSS, and secret-safety contracts.
5. Run focused frontend/API tests, full relevant regressions if needed, secret scan, and `git diff --check`.

## Validation commands

```
python -m pytest tests/test_settings_tab_refactor_frontend.py -q -rs
python -m pytest tests/test_external_api.py tests/test_unified_mailbox_catalog.py -q -rs
rg -n "dk_[0-9a-fA-F]{20,}|DUCKMAIL_BEARER_TOKEN\s*=\s*dk_|Bearer\s+dk_" templates static tests .trellis docs README.md README.en.md .env.example docker-compose.yml mailops
git diff --check
```
