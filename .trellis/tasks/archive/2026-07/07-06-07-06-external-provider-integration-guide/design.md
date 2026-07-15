# External Provider Integration Guide Design

## Contract Boundary

`outlook_web.services.provider_catalog` owns the provider integration guide because it already owns the provider catalog, deployment profile, selection policy, diagnostics, alias contract, and endpoint constants. Controllers and OpenAPI must consume this service output rather than reassembling provider instructions locally.

The guide is discovery metadata only. It may expose provider names, env key names, settings key names, examples with provider values, endpoint paths, and readiness states. It must not expose env values, settings values, API keys, bearer tokens, passwords, JWTs, consumer keys, task tokens, or raw provider secrets.

## Data Sources

The guide is derived from these existing contracts:

- `get_mailbox_provider_catalog(include_inactive=True, strict=False)` for provider identity, kind, label, active state, selection, configuration, deployment snippets, and capabilities.
- `get_mailbox_provider_deployment_profile(strict=False)` for provider values, aliases, config templates, and deployment examples.
- `get_mailbox_provider_selection_policy(deployment_profile=...)` for source priority and request/default scope metadata.
- `get_active_mailbox_provider_filter_contract(strict=False)` for allowlist status and alias recognition.
- `get_mailbox_provider_diagnostics(include_inactive=True)` for local readiness and missing config summaries.
- External endpoint constants already assembled by capabilities for provider discovery, provider health, unified mailbox directory, pool claim, and task temp-mail apply.

## Output Shape

The guide is a versioned object with top-level `version`, `source_priority`, `secret_policy`, `workflow`, `aliases`, `provider_filter`, `endpoints`, and `providers`.

Each provider entry includes `provider`, `label`, `kind`, `active`, readiness fields, env and settings key lists, secret key lists, deployment examples, request override examples, directory filter examples, health endpoint metadata, aliases, capabilities, and config-file guidance. Provider entries are keyed by canonical catalog provider names. Alias-only values such as `imap` stay in the top-level alias contract and workflow guidance unless they also exist as catalog providers.

## Compatibility

GPTMail aliases remain visible through `legacy_bridge`, `custom_domain_temp_mail`, `legacy_gptmail`, `gptmail`, and `temp_mail` relationships already exposed by `get_provider_alias_contract()`. The account-level `imap` pool/allowlist alias remains visible in aliases and workflow guidance without being converted into a fake temp provider.

## API Surfaces

The same helper result is embedded in `/api/external/capabilities`, `/api/external/providers`, internal `/api/providers`, and unified mailbox directory `provider_context`. OpenAPI exposes it as a typed-but-extensible `ProviderIntegrationGuide` schema and requires it in `CapabilitiesData` and `MailboxProviderContext`.

## Validation

Focused tests cover external providers, external capabilities/OpenAPI, and unified mailbox directory. Assertions verify DuckMail env requirements, Mail.tm API base guidance, request fields, alias preservation, endpoint paths, and absence of known secret values. Full pytest remains the final gate.
