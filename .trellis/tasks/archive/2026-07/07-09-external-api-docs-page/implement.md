# External API docs page Implementation Plan

## Steps

1. Read applicable backend/frontend specs and current external API route/provider catalog implementation.
2. Add `docs` to the external endpoint/documentation discovery contract.
3. Implement `outlook_web/services/external_api_docs.py` as a zero-dependency HTML renderer from the OpenAPI contract.
4. Add guarded controller/route wiring for `/api/v1/external/docs` and `/api/external/docs`.
5. Add focused tests for auth, HTML content, alias compatibility, generated endpoint list, discovery metadata, and secret safety.
6. Update README / README.en if needed and mark the project-map OpenAPI / Swagger docs item complete.
7. Run focused and neighboring regression checks.

## Validation Commands

- `python -m pytest tests/test_external_api_docs_page.py -q`
- `python -m pytest tests/test_external_api_versioned_aliases.py tests/test_external_api.py tests/test_unified_mailbox_catalog.py -q`
- `python -m pytest tests/test_security_headers.py -q`
- `python -m py_compile outlook_web/controllers/system.py outlook_web/routes/system.py outlook_web/services/external_api_docs.py outlook_web/services/external_api_openapi.py outlook_web/services/provider_catalog.py`
- `git diff --check`

## Risk Notes

- Keep docs route authenticated; otherwise deployments may reveal enabled provider shape to the public.
- Avoid external assets so the docs page works behind strict networks and current CSP.
- Escape generated HTML from dynamic contract values.
- Do not duplicate the OpenAPI path list manually; tests should prove endpoint rows are generated from `paths`.
