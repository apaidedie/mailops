# Provider integration guide UI

## Goal

Expose the existing `provider_integration_guide` contract in the authenticated admin UI so an operator can see how to activate a mailbox provider, make it a runtime or pool default, call it from external APIs, and copy a safe deployment snippet without reading the raw API payload.

## Background

The backend already returns `provider_integration_guide` from `/api/providers`, `/api/external/providers`, `/api/external/capabilities`, OpenAPI capability metadata, and unified mailbox `provider_context`. The current settings UI consumes `mailbox_providers`, `provider_diagnostics`, and `deployment_profile`, but it does not cache or render `provider_integration_guide`. That leaves the newly exposed guide useful for API clients but hidden from the admin workflow.

## Requirements

The settings page must add a compact Provider integration guide area near the existing provider diagnostics, deployment templates, and provider console. The UI should reuse `/api/providers` and the existing vanilla JavaScript/CSS stack, with no new frontend framework or package.

The guide must show the current source priority, discovery endpoint, secret policy, active allowlist mode, and per-provider deployment/call information. It must support scanning all providers and focusing on temp providers, because the immediate operator problem is temporary mailbox integration while the guide also covers account-pool aliases.

Each rendered provider entry must show provider label/key, readiness state, required env keys, optional env keys, settings keys, activation setting, runtime default if available, pool default, pool claim request field, task temp-mail apply request field when available, and aliases when present.

The copy action must generate a provider-specific `.env` snippet from the guide and configuration contract. Secret variables may appear by key name only with empty values. The UI must not expose real bearer tokens, API keys, passwords, task tokens, JWTs, consumer keys, or legacy secret field values.

The implementation must preserve existing provider console behavior, health probing, config templates, plugin provider handling, and GPTMail compatibility alias semantics. Do not rename `legacy_bridge` internally or remove GPTMail aliases from the guide.

## Acceptance Criteria

- The settings page contains a `providerIntegrationGuide` mount with all/temp filters and a disabled-safe loading/empty state.
- `loadMailboxProviderCatalog()` caches `data.provider_integration_guide`, clears it on fetch failure, and renders the guide together with diagnostics and config templates.
- The guide renderer uses guide data from `/api/providers` rather than hardcoded provider instructions.
- Copying a provider snippet uses empty values for secret env keys and includes activation/default/request examples when the guide exposes them.
- Frontend contract tests cover the new DOM ids/classes, JS cache/render/copy functions, `/api/providers` `provider_integration_guide` consumption, and secret-token non-exposure.
- Targeted tests pass for the settings frontend and provider/API contracts touched by this UI.

## Out Of Scope

This task does not change provider resolution, provider config-file parsing, OpenAPI schemas, external API behavior, provider plugin contracts, or upstream network probing semantics.
