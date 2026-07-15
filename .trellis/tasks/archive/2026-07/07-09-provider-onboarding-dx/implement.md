# Provider Onboarding DX Implementation Plan

## Steps

- [x] Add a base-class check to `outlook_web/services/temp_mail_provider_contract.py` without changing the response envelope shape.
- [x] Add regression coverage in `tests/test_temp_mail_provider_contract_validation.py` for non-base provider classes.
- [x] Update provider factory / plugin API expectations where existing loose test providers now report invalid contract validation.
- [x] Strengthen `tests/test_temp_mail_provider_plugin_template.py` and scaffold assertions so the template inheritance requirement is explicit.
- [x] Update `docs/provider-onboarding.md` and `临时邮箱Provider插件接入说明.md` with the validated onboarding sequence and hard base-class gate.

## Validation Commands

```powershell
python -m pytest tests\test_temp_mail_provider_contract_validation.py tests\test_temp_mail_provider_plugin_template.py tests\test_temp_mail_plugin_cli.py tests\test_temp_mail_plugin_api.py tests\test_temp_mail_plugin_factory.py -q
python scripts\project_readiness_check.py
git diff --check
```

## Review Gates

- Contract validation output remains secret-free.
- No provider-specific routing or endpoint behavior changes are introduced.
- Documentation examples do not contain real secrets.
