# Provider Onboarding DX Design

## Boundary

This task touches the temp-mail provider validation boundary and provider onboarding docs. It does not change provider runtime routing, API endpoints, database schema, or frontend rendering.

## Contract Change

`validate_temp_mail_provider_class(provider_name, provider_cls, *, probe_options=False)` will treat `issubclass(provider_cls, TempMailProviderBase)` as a required structural check. Non-base classes receive a stable `PROVIDER_BASE_CLASS_INVALID` error issue and `status=invalid`.

The returned payload shape stays unchanged:

- `checks` gains a `base_class` check.
- `issues` gains the machine-readable error for non-base classes.
- `summary`, `status`, and `valid` continue to be derived from issues.
- `safe_metadata` remains secret-free and keeps existing fields.

## Compatibility

The registry and catalog may still contain legacy loose classes in tests or old plugin installations. The change does not remove them from discovery; it marks their `contract_validation` as invalid so operators have a clear readiness signal before routing them in production.

Built-in providers and the scaffold template already inherit `TempMailProviderBase`, so they should remain valid.

## Documentation

The onboarding docs should make the order explicit:

1. Generate or copy the scaffold.
2. Keep the provider inheriting `TempMailProviderBase` and registered with `@register_provider`.
3. Replace the upstream adapter.
4. Run `python web_outlook_app.py validate-provider <provider_key> --file <plugin.py>`.
5. Enable or reload only after `contract_validation.status=valid`.

## Rollback

Rollback is limited to reverting the validation check, tests, and documentation. No migration or data cleanup is required.
