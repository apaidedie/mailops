# Provider Contract Status UI Design

## Architecture

Keep the backend as the source of truth. The settings UI consumes additive metadata already returned by provider/plugin APIs and renders a compact operational surface.

Primary UI state:

- `providerContractState.catalog`: contract rows derived from `/api/providers` `mailbox_providers` and, when needed, `provider_integration_guide.providers`.
- `providerContractState.plugins`: compact contract summaries from `/api/plugins` provider plugin rows.
- `providerContractState.lastUpdated`: local display timestamp for the operator.

No validation is reimplemented in JavaScript. The UI only normalizes display fields, derives counts, and sorts invalid/warning providers ahead of valid providers.

## Data Flow

```text
loadMailboxProviderCatalog()
  -> data.mailbox_providers + data.provider_integration_guide.providers
  -> updateProviderContractStateFromCatalog(data)
  -> renderProviderContractStatus()

loadInstalledPlugins()
  -> plugin list rows with contract_validation summaries
  -> updateProviderContractStateFromPlugins(data)
  -> renderProviderContractStatus()
```

## UI Composition

The panel lives near existing provider diagnostics/integration guide controls. It contains:

- Header with title, short helper copy, and last-updated text.
- Four compact counters: valid, warning, invalid, unknown.
- Provider rows with status badge, label/key/kind, summary counts, issue-code chips, and plugin state if available.
- Empty state when no contract-aware temp providers are available.

Visual direction: operational SaaS. Use existing blue/green/orange/red semantic colors, calm borders, compact rows, and responsive wrapping. No decorative animations are required.

## Secret Policy

Render only contract summaries and issue codes. Never render `safe_metadata`, raw config fields, raw `checks`, raw `issues.message`, raw plugin config, API keys, provider bearer tokens, JWTs, passwords, refresh tokens, consumer keys, or task tokens.

## Compatibility

The change is additive. If `/api/plugins` has not loaded, catalog rows remain useful. If old payloads lack `contract_validation`, the UI shows `unknown` rather than failing.

## Rollback

Remove the mount, state helpers, render function, styles, and tests. No database or API rollback is required.
