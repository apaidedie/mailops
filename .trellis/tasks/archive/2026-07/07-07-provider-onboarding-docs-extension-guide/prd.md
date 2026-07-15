# Provider onboarding docs and extension guide

## Goal

Make provider onboarding easier to follow for both humans and automation clients by aligning the public README, provider plugin guide, example provider config files, and machine-readable provider discovery payloads.

This task should turn the current scattered provider notes into a coherent path: discover capabilities, choose an active/default provider through env/config/settings/request fields, then add future temp-mail providers through the plugin contract without modifying core routes.

## Confirmed Facts

- Provider discovery already exposes `deployment_profile`, `selection_policy`, `provider_integration_guide`, and `integration_manifest` through `/api/external/capabilities`, `/api/external/providers`, admin `/api/providers`, and unified mailbox provider context.
- Provider selection priority is already `env`, `provider_config_file`, `settings`, then `default`.
- Current external payloads expose secret key names such as `DUCKMAIL_BEARER_TOKEN`, but tests require secret values to stay empty and forbid DuckMail-style token leakage.
- `.env.example`, `.runtime/providers.example.json`, and `.runtime/providers.example.toml` already exist, but the human onboarding path is spread across README sections and separate Chinese plugin docs.
- Plugin docs correctly warn that runtime plugins are loaded from `<DATABASE_PATH parent>/plugins/temp_mail_providers/` as flat `*.py` files.
- Future provider extensibility should keep using catalog/capability/selection-policy contracts rather than adding provider-specific API or UI tables.

## Requirements

- Add a concise provider onboarding document that explains the first-run integration path for external projects and the extension path for new temp-mail providers.
- Make the machine-readable provider discovery payload expose stable documentation pointers so clients and operators can find the human docs from capabilities/provider discovery without scraping README text.
- Keep all new discovery fields secret-safe. No API key, bearer token, JWT, password, refresh token, consumer key, task token, or stored provider secret value may be echoed.
- Keep existing endpoint paths, provider names, aliases, request fields, environment variable names, config-file sections, and selection priority unchanged.
- Keep `.env.example`, JSON example, TOML example, README, plugin docs, OpenAPI schema, and provider catalog tests aligned with the documented onboarding contract.
- Use focused regression tests to prove the discovery payload and OpenAPI contract include the new documentation pointers and still do not leak secrets.

## Acceptance Criteria

- `README.md` and `README.en.md` link to the new onboarding guide from the provider/external integration area.
- A dedicated provider onboarding guide documents the recommended sequence: capabilities, providers, mailboxes, provider health, pool claim, task temp-mail apply, and plugin extension.
- `integration_manifest`, `provider_integration_guide`, and mailbox `provider_context` include a `documentation` object with stable local doc paths and machine-readable purpose labels.
- OpenAPI schemas include the new documentation object for affected payloads.
- Example provider config files remain valid and are referenced by the onboarding guide.
- Regression tests cover the new documentation object and verify secret values remain absent.
- Relevant Python and static JS syntax checks pass; focused provider/external contract tests pass.

## Notes

- This task is intentionally additive. It should not rename `gptmail` aliases, change provider request fields, or remove legacy bridge compatibility.
