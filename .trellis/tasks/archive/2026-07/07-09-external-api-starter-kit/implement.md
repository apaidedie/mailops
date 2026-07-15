# External API starter kit Implementation Plan

## Steps

1. Read backend provider-selection contract and quality guidelines.
2. Add `examples/external_api_python_client.py` with stdlib-only client and CLI.
3. Add unit tests for the client using mocked transport.
4. Update `docs/external-integration-quickstart.md`, `README.md`, and `README.en.md` to point to the starter.
5. Run focused tests and syntax checks.
6. Inspect diff for secret leaks and unrelated changes.

## Validation Commands

- `python -m pytest tests/test_external_api_python_client.py -q`
- `python -m pytest tests/test_external_api_smoke_script.py tests/test_external_api_docs_page.py tests/test_external_api_versioned_aliases.py -q`
- `python -m py_compile examples/external_api_python_client.py scripts/external_api_smoke.py`
- `git diff --check`
- `rg -n "dk_[0-9a-fA-F]{20,}|DUCKMAIL_BEARER_TOKEN=.*dk_|X-API-Key: [A-Za-z0-9_.-]{20,}" examples docs README.md README.en.md tests/test_external_api_python_client.py`

## Risk Notes

- Do not accidentally make the CLI mutate server state in the default `discover` path.
- Do not embed real provider tokens or API keys in examples or tests.
- Keep the starter independent from Flask app internals so external projects can copy it.
- Ensure `verification_flow` closes sessions even when reads fail.
