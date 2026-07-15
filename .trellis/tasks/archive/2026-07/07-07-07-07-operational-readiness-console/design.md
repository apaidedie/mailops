# Operational Readiness Console Design

## UI Brief

Audience: operators who are configuring the project for personal use or exposing it to external services. They need a quick operational answer, not marketing copy.

Primary workflow: open Settings -> API Security and see whether API auth, provider catalog, mailbox inventory, provider defaults, pool, and task temp-mail creation are ready.

Product archetype: operational SaaS control surface. The design should be dense, calm, and scannable.

Constraints: existing Flask template, plain JavaScript, plain CSS, current Settings external API command center, and bilingual i18n. No new UI package.

Source of truth: `/api/settings`, `/api/providers`, and authenticated `/api/mailboxes` provider context. The browser must not call `/api/external/*` for this admin console.

States: loading, ready, provider catalog degraded, mailbox snapshot degraded, and no mailbox inventory.

Acceptance: frontend contract tests, JavaScript syntax checks, focused API/UI tests, and secret scan.

## Data Flow

`loadSettings()` stores `externalApiSettingsSnapshot` and renders the external command center.

`loadMailboxProviderCatalog()` stores provider diagnostics, deployment profile, integration guide, manifest, and quickstart, then rerenders the command center.

New `loadOperationalReadinessSnapshot()` fetches `/api/mailboxes?kind=all&status=all&provider=all&sort=updated_desc&page=1&page_size=1` after settings load. It stores only `summary`, `provider_context`, `contract`, and `facets` in `operationalReadinessSnapshotCache`, then rerenders the command center.

`renderOperationalReadinessConsole(settings, state)` combines those caches into a read-only panel. It does not read DOM input values.

## UI Placement

The console renders inside `renderExternalApiCommandCenter()` after the top metrics and before Quickstart. This gives operators the product-level readiness answer before endpoint examples.

## Readiness Model

The console uses generic status cards:

- External API: ready when API key or multi-key is configured, degraded otherwise.
- Provider catalog: ready when `/api/providers` loaded, degraded on provider error.
- Mailbox directory: ready when `/api/mailboxes` snapshot loaded, degraded if loading failed.
- Account mailbox inventory: ready when account count is positive, neutral when zero.
- Temp-mail inventory: ready when temp count is positive, neutral when zero.
- Pool: ready, partial, disabled, or neutral based on existing pool settings helper.
- Task temp-mail: ready when provider diagnostics show at least one active ready dynamic-create provider.
- Discovery/OpenAPI: ready when endpoint map contains capabilities and OpenAPI paths.

## Secret Safety

The console consumes only cached settings booleans/counts and provider/mailbox discovery objects. It must not reference `settingsExternalApiKey`, `settingsExternalApiKeysJson`, `settingsDuckmailBearerToken`, `settingsEmailnatorApiKey`, `settingsTempMailApiKey`, or provider secret values.

## Styling

Use the existing command-center visual system: compact cards, restrained borders, semantic status color, stable grid dimensions, `overflow-wrap: anywhere`, and mobile single-column collapse.
