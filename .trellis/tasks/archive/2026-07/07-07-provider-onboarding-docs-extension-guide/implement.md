# Provider onboarding docs and extension guide implementation plan

## Checklist

- Add a shared provider documentation contract helper in `outlook_web.services.provider_catalog`.
- Embed the documentation contract in provider integration guide, external integration manifest, and mailbox provider context.
- Add OpenAPI schema coverage for the documentation contract and reference it from affected schemas.
- Create a concise onboarding guide under `docs/` that connects external discovery, env/config selection, example files, health checks, and plugin extension.
- Update Chinese and English README docs to point to the new guide.
- Update plugin docs only if the onboarding guide changes an existing instruction or cross-link.
- Add focused tests for documentation fields and secret-safe behavior.
- Run syntax checks and focused provider/external tests.

## Validation commands

```bash
python -m pytest tests/test_external_api.py tests/test_multi_mailbox.py tests/test_unified_mailbox_catalog.py -q -rs
node --check static/js/main.js
node --check static/js/i18n.js
rg -n "dk_[0-9a-fA-F]{20,}|DUCKMAIL_BEARER_TOKEN\s*=\s*dk_|Bearer\s+dk_" templates static tests .trellis docs README.md README.en.md .env.example docker-compose.yml outlook_web
git diff --check
```

## Risk points

- Do not add real secret values to docs, examples, tests, or snapshots.
- Do not change selection priority, provider aliases, request fields, endpoint paths, or config-file sections.
- Keep the OpenAPI additions broad enough for future docs entries without overfitting to one path.
