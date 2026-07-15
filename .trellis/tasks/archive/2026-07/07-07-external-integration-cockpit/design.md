# External Integration Cockpit Design

## Scope

This task upgrades the existing Settings external API command center. It does not add new backend routes, change auth, change provider selection semantics, or replace the current starter snippets, workflows, and provider recipe panels.

## UI Brief

Audience: operators and developers connecting external automation services to the unified Outlook/IMAP/temp-mail platform.

Primary workflow: open Settings, confirm external API readiness, read the shortest quickstart path, then copy a secret-free integration packet.

Product archetype: operational SaaS, dense but calm, using the existing Flask template plus plain CSS/JS stack.

Source of truth: `/api/providers.quickstart`, falling back to `/api/providers.integration_manifest.quickstart`.

States: loading, provider catalog unavailable, ready, no quickstart, copy success/failure, narrow viewport.

Acceptance: focused frontend contract tests plus rendered smoke check if the app can be started locally.

## Data Flow

`loadMailboxProviderCatalog()` reads `/api/providers` and stores `data.quickstart` in a new cache. The UI helper `getExternalIntegrationQuickstart()` returns that top-level cache first, then falls back to `getExternalIntegrationManifest().quickstart`.

`renderExternalApiCommandCenter()` renders the new quickstart block from this helper before the endpoint and starter snippet panels. Existing starter snippets may continue using manifest helpers, but discovery steps should naturally benefit from quickstart where useful.

## UI Shape

The cockpit uses one compact section with three zones: auth/sequence summary, provider selector fields, and request examples. It uses existing card-like command center styling, restrained blue/neutral status accents, monospace code blocks for request bodies, and responsive grids that collapse to one column.

## Secret Safety

The quickstart copy text is built only from the quickstart object. It must not include provider env hints or manifest provider credential keys. Tests assert `DUCKMAIL_BEARER_TOKEN` and real token-like values are absent.

## Compatibility

The change is additive. If quickstart is unavailable, the command center keeps showing the existing endpoint, starter snippet, workflow, and recipe panels.
