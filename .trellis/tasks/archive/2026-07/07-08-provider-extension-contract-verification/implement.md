# Provider Extension Contract Verification Implementation Plan

## Checklist

1. Add focused backend tests for the validator service:
   - valid provider returns `valid`.
   - missing/invalid metadata returns structured issues.
   - secret defaults are flagged and absent from safe metadata.
2. Add plugin API tests:
   - `GET /api/plugins` includes compact contract validation state for a loaded plugin.
   - `GET /api/plugins/<name>/contract` returns full validation.
   - unknown plugin returns `PLUGIN_NOT_LOADED`.
3. Add provider discovery tests proving one plugin provider carries the same validation status through:
   - `get_available_providers()`.
   - `get_mailbox_provider_catalog()` / `/api/providers` catalog item.
   - `provider_integration_guide.providers`.
   - `integration_manifest.providers`.
4. Implement `outlook_web/services/temp_mail_provider_contract.py`.
5. Attach validation in `temp_mail_provider_factory.get_available_providers()`.
6. Pass through validation in `provider_catalog` catalog items, diagnostics, integration guide, and manifest provider entries.
7. Add plugin manager/controller/route support for `/api/plugins/<name>/contract`.
8. Update `docs/provider-onboarding.md` and backend provider-selection spec with the new validation contract.
9. Run targeted tests and `git diff --check`.

## Validation Commands

```bash
python -m pytest tests/test_temp_mail_provider_contract.py -q
python -m pytest tests/test_temp_mail_plugin_manager.py tests/test_temp_mail_plugin_api.py -q
python -m pytest tests/test_multi_mailbox.py tests/test_external_temp_emails_api.py -q
python -m pytest tests/test_external_api.py tests/test_external_api_smoke_script.py -q
git diff --check
```

If the broader external API suite is too slow for the current slice, run the focused tests first and then the discovery/OpenAPI tests that cover touched contracts.

## Risk Points

- Do not call provider mailbox mutation methods from validation.
- Do not expose raw `get_options()` values in validation payloads.
- Do not create provider-name branches in frontend/controllers.
- Keep validation additive so existing clients remain compatible.
