# Design

## Architecture

`provider_catalog` remains the source of truth. Each temp provider receives a `settings_ui` projection that describes selector text, aliases, panel mode (`schema`, `legacy_bridge`, `cloudflare`), and editable fields. The frontend normalizes only contract shape; it does not infer behavior from provider names.

## Data Flow

Provider factory/catalog metadata -> `get_mailbox_provider_catalog()` -> authenticated provider/settings payload -> catalog cache in `main.js` -> selector and field rendering -> existing `/api/settings` save flow.

## Compatibility

Legacy aliases canonicalize through catalog metadata. Specialized panels remain mounted but are selected by `settings_ui.panel`. If discovery fails, selectors show an unavailable state instead of silently presenting a stale hard-coded list.

## Security

Catalog fields include setting key names and masked state only. Secret values are never included. Generic save behavior uses existing secret masking rules and only submits changed values.

## Trade-offs

Special panels remain temporarily because Cloudflare and the legacy bridge include provider-specific actions beyond simple fields. The contract makes this explicit and permits later migration to fully generic controls without another provider-name switch.
