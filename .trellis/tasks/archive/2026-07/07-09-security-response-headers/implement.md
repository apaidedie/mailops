# Security response headers middleware Implementation Plan

## Steps

1. Add config helpers for enabling security headers, forcing HSTS, and configuring HSTS max age.
2. Add `mailops/middleware/security_headers.py` with CSP/header constants and `attach_security_headers(response)`.
3. Export the middleware from `mailops/middleware/__init__.py` and register it in `mailops/app.py`.
4. Add focused tests for HTML/API/static responses, HSTS secure vs local HTTP behavior, setdefault/no-overwrite behavior, and extension CORS compatibility.
5. Mark the security response header item complete in `docs/项目地图.md`.
6. Run focused tests and syntax checks.

## Validation Commands

- `python -m pytest tests/test_security_headers.py tests/test_smoke_contract.py tests/test_error_and_trace.py -q`
- `python -m pytest tests/test_external_api_versioned_aliases.py -q`
- `python -m py_compile mailops/app.py mailops/config.py mailops/middleware/security_headers.py mailops/middleware/__init__.py`
- `git diff --check`

## Risk Notes

- Keep CSP compatible with existing inline scripts/styles; strict nonce CSP is a separate refactor.
- HSTS must not appear on ordinary local HTTP responses by default.
- Flask-CORS may run after or before this middleware; tests should only require security headers and CORS headers to coexist, not a specific hook order.
