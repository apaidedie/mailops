# Provider Plugin Template

## Goal

Make future temp-mail provider additions faster and safer by shipping a copyable plugin template that already satisfies the current `TempMailProviderBase` and contract-validation rules.

## Background

- The project already supports third-party temp-mail provider plugins from `<DATABASE_PATH parent>/plugins/temp_mail_providers/*.py`.
- Provider contract validation is exposed through provider catalogs and plugin APIs, but new provider authors currently have to infer the required class shape from tests or built-in providers.
- A minimal, tested template improves extensibility without changing runtime routing or external API behavior.

## Requirements

- Add a copyable example plugin under `examples/` that inherits `TempMailProviderBase` and uses `@register_provider`.
- The template must implement every required provider method: options, create/delete mailbox, list/detail/delete/clear messages.
- The template must show safe config schema patterns, including secret fields without default values.
- The template must be network-adapter oriented: provider authors can replace small request-normalization helpers rather than editing core app code.
- The template must not execute network requests during import or contract validation.
- Update provider onboarding documentation to point future provider authors to the template.
- Add tests proving the template imports, registers under the expected provider key in isolation, and passes `validate_temp_mail_provider_class(..., probe_options=True)` without leaking placeholder secret values.

## Acceptance Criteria

- [x] `examples/temp_mail_provider_plugin_template.py` exists and is a valid temp-mail provider plugin example.
- [x] The template contract validation status is `valid` with zero errors when loaded under its provider key.
- [x] Tests assert secret config fields in the template have no default values and do not leak placeholder secrets through validation output.
- [x] `docs/provider-onboarding.md` links to the template in the future-provider section.
- [x] No provider-specific runtime routing, external API paths, or database schema are changed.
- [x] Focused provider contract/plugin tests pass.

## Out Of Scope

- Adding another real third-party provider.
- Changing plugin loader semantics or registry paths.
- Building a UI wizard for provider creation.
