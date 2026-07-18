# External Provider Integration Guide Implementation Plan

## Steps

- Add `get_provider_integration_guide(...)` in `mailops.services.provider_catalog`, with optional prebuilt inputs so callers can reuse the same deployment profile, selection policy, diagnostics, provider filter, and endpoint map.
- Build provider entries from catalog items plus diagnostics and deployment snippets. Keep secret values out by copying only key names and redacted/default-free examples.
- Add the guide to external capabilities, external providers, internal providers, and mailbox directory provider context.
- Extend OpenAPI schemas with `ProviderIntegrationGuide`, require it in `CapabilitiesData` and `MailboxProviderContext`, and keep schema details broad enough for future providers.
- Update tests for external provider discovery, capabilities/OpenAPI, and unified mailbox directory provider context.
- Update backend spec so future provider discovery changes preserve this guide.

## Validation Commands

- `$env:PYTHONIOENCODING='utf-8'; python -m pytest tests/test_external_api.py tests/test_external_temp_emails_api.py tests/test_unified_mailbox_catalog.py -q`
- `git diff --check`
- `$env:PYTHONIOENCODING='utf-8'; python -m pytest -q`

## Review Gates

- The guide must be generated from existing provider contracts, not a new hardcoded provider registry.
- Secret key names may appear, but secret values must not appear in response payload tests.
- OpenAPI provider override enums remain derived from `selection_policy`, not the guide.
