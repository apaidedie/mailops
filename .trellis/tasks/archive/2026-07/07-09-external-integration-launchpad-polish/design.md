# External integration launchpad polish design

## Architecture

This task is a frontend/admin productization layer over existing backend contracts. It does not add a new API or duplicate the external integration bundle server logic.

The Settings -> API Security command center remains the single entry point for external integration UI. A new launchpad panel is rendered inside `renderExternalApiCommandCenter()` using the same cached data already loaded by the page:

- settings snapshot from `/api/settings`
- provider catalog, guide, manifest, and quickstart from `/api/providers`
- mailbox readiness snapshot from `/api/mailboxes?page_size=1`

The panel is a display and copy adapter only. It does not call `/api/v1/external/integration-bundle` from the browser because that endpoint requires external API-key auth and the admin page must not read or reuse configured API keys.

## Data Flow

1. `loadMailboxProviderCatalog()` caches `/api/providers` payloads including `integration_manifest`, `provider_integration_guide`, and `quickstart`.
2. `loadOperationalReadinessSnapshot()` caches compact mailbox readiness from `/api/mailboxes`.
3. `renderExternalApiCommandCenter(settings, state)` computes existing access/provider/pool/source summaries.
4. New launchpad helpers derive:
   - canonical endpoint from existing endpoint maps or stable fallback `/api/v1/external/integration-bundle`
   - legacy alias from stable fallback `/api/external/integration-bundle`
   - placeholder auth from `getExternalIntegrationManifestAuth()`
   - readiness/status facts from existing access/provider/readiness summaries
   - copy command using placeholder API key only
5. Event delegation handles `data-external-api-bundle-copy` and copies the placeholder curl command.

## UI Shape

The launchpad panel appears after the onboarding checklist and smoke-check panel, before the metrics/readiness/quickstart sections. This keeps the first viewport focused on what an external integrator should do first while preserving detailed diagnostics below.

The panel uses the existing command-center visual language: 8px radius, restrained borders, status badges, monospaced endpoint text, and compact cards. It includes:

- title/subtitle identifying the integration readiness bundle
- summary cards for auth, discovery route, provider readiness, and mailbox inventory
- canonical and legacy endpoint rows
- copyable placeholder curl command

## Compatibility

- Canonical v1 paths remain preferred; legacy alias is displayed as compatibility metadata.
- Existing snippets, quickstart, recipes, workflow playbooks, and mailbox session lifecycle keep their current helpers and copy behavior.
- The endpoint list gains `integration_bundle`; code using existing keys is unaffected.
- The smoke coverage list gains the bundle endpoint so the UI aligns with `scripts/external_api_smoke.py`.

## Safety

- Do not read `settingsExternalApiKey`, `settingsExternalApiKeysJson`, provider token inputs, or masked placeholders in launchpad helpers.
- Do not branch on provider names. Provider readiness is counted from generic summary/cache fields.
- Copy text must contain only `X-API-Key: <your-api-key>`.
- Long endpoint paths and commands use `overflow-wrap: anywhere` and responsive one-column collapse.

## Rollback

The change is isolated to static frontend assets and frontend contract tests. Rollback removes the new helper/render/copy/CSS/i18n additions and the added endpoint-list entry. Backend contracts are unchanged.
