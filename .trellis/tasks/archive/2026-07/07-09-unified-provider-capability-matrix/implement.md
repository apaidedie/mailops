# Implementation Plan

## Checklist

1. Add provider-catalog helpers for capability matrix rows, workflow groups, and totals.
2. Attach `capability_matrix` to `get_mailbox_provider_readiness_summary()`.
3. Add OpenAPI schemas and wire the readiness summary schema to the matrix.
4. Add or update external API tests for provider discovery, integration bundle propagation, OpenAPI schema coverage, and secret safety.
5. Update quickstart/provider onboarding docs with the matrix as the selection source.
6. Run targeted tests and readiness checks.

## Validation Commands

```powershell
python -m pytest tests\test_external_api.py -q -k "provider_capability_matrix or provider_readiness or integration_bundle or openapi"
python scripts\project_readiness_check.py
git diff --check
```

## Risk Points

- Do not duplicate provider defaults or routing rules outside provider catalog helpers.
- Do not expose provider secret values through matrix row metadata.
- Keep this additive so existing clients relying on readiness summary do not break.
