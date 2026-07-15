# Provider selection recipes

## Goal

Expose provider-selection recipes that external projects and the Settings UI can consume directly when choosing active mailbox sources, default temp-mail providers, default pool-claim providers, and per-request provider overrides.

## Background

The backend already exposes `selection_policy`, `deployment_profile.templates`, `provider_integration_guide`, and `integration_manifest.workflows`. These contracts are useful but still require callers to combine several fields when they want a concrete answer to questions such as how to activate only DuckMail, how to make Mail.tm the task-temp provider, or how to claim a mailbox from a specific provider for one request.

## Requirements

- Add machine-readable provider-selection recipes derived from the existing provider catalog, deployment profile, selection policy, and provider integration guide.
- Cover active allowlist, temp runtime default, pool claim default, explicit pool claim, and task temp apply flows.
- Include env, provider-config-file JSON/TOML object shapes, settings keys, request fields, provider value, source priority, and endpoint metadata where applicable.
- Keep recipes provider-agnostic and generated from catalog data. Do not add provider-name branches for DuckMail, Mail.tm, GPTMail, TempMail.lol, Emailnator, or future providers.
- Keep recipes secret-safe. Secret key names may appear in provider env hints, but recipe values must not include secret values.
- Surface recipes through `deployment_profile`, `selection_policy`, `provider_integration_guide`, and `integration_manifest` without breaking existing payload fields.
- Type the new recipe payload in OpenAPI where the integration manifest schema is exposed.

## Acceptance Criteria

- `/api/external/capabilities` returns recipe data under `deployment_profile`, `selection_policy`, `provider_integration_guide`, and `integration_manifest`.
- Recipes are derived from `selection_policy.scopes.*.allowed_values` and provider guide entries; a synthetic future provider can appear without editing a separate recipe enum.
- Recipe payloads include env, provider config JSON/TOML, settings, and request examples for at least `duckmail`, `mail_tm`, and `legacy_bridge` when those providers are present.
- Recipe payloads do not contain real provider secret values and pass the existing DuckMail token leak scans.
- OpenAPI exposes typed recipe schemas instead of loose untyped objects.
- Provider/API regression tests pass.

## Out Of Scope

This task does not redesign the Settings UI. UI rendering for the recipes can be a later child task unless small copy/display changes are needed to keep existing panels coherent.
