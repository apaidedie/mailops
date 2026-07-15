# Provider workbench IA polish design

## Boundary

This task changes Settings -> API Security information architecture and visual polish only. Backend provider contracts stay unchanged. The workbench remains a display adapter over authenticated settings data plus `/api/providers` discovery caches.

## Source Of Truth

- Settings snapshot: `externalApiSettingsSnapshot` and `data.settings` from `/api/settings`.
- Provider discovery caches: `mailboxProviderDiagnosticsCache`, `mailboxProviderDeploymentProfileCache`, `mailboxProviderIntegrationGuideCache`, and `mailboxProviderIntegrationManifestCache` populated by `loadMailboxProviderCatalog()`.
- Endpoint and selection data: `provider_integration_guide`, `selection_policy`, and `integration_manifest` from existing backend payloads.

## UI Shape

The workbench should read as one operations-console surface. The first block answers current routing posture, provider readiness, defaults, config-file state, source priority, and secret posture. The detailed diagnostics, deployment templates, integration guide, and provider console remain below as drill-down sections.

Use a restrained SaaS dashboard treatment: compact headings, stable metric tiles, muted helper copy, predictable filter controls, and strong text wrapping for long source-priority strings, config-file paths, and provider names.

## Compatibility And Secret Safety

Render helpers must not read credential input elements such as `settingsExternalApiKey`, `settingsExternalApiKeysJson`, `settingsDuckmailBearerToken`, `settingsEmailnatorApiKey`, or `settingsTempMailApiKey`. Secret key names from discovery metadata may be displayed; secret values must never render or copy.

## Validation

Run frontend contract tests covering provider workbench mounts, render helpers, source-cache usage, secret-safety slices, CSS hooks, and mobile wrapping. Run JS syntax checks and rendered browser QA on desktop and mobile because CSS/layout changes are expected.
