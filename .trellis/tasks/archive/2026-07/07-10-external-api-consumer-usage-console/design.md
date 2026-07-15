# External API consumer usage console design

## Architecture

This task is frontend-only unless implementation uncovers missing data. The existing settings API is the source of truth for configured consumers and today usage counters.

Data path:

1. `outlook_web.controllers.settings.api_get_settings()` returns `settings.external_api_keys`.
2. Each key item is enriched by `external_api_keys_repo.get_external_api_usage_summary()`.
3. `static/js/main.js` stores the response in `externalApiSettingsSnapshot` and renders the API Security command center.
4. The new consumer usage console is rendered from `safeSettings.external_api_keys` inside `renderExternalApiCommandCenter()`.

## UI Contract

- Section title: `外部 API 消费方`.
- Summary row: total configured consumers, enabled consumers, consumers used today, and consumers with errors today.
- Consumer rows/cards: name, consumer key, enabled state, access scope, pool access, today total/success/error counts, and last used timestamp.
- Empty state: safe copy explaining that no multi-key consumers are configured yet.
- Visual tones:
  - `disabled`: disabled consumer.
  - `warning`: enabled consumer with zero usage today.
  - `danger`: consumer with errors today.
  - `ready`: enabled consumer with successful usage and no errors today.

## Security

- The renderer must not read `settingsExternalApiKey`, `settingsExternalApiKeysJson`, or any password/secret input.
- The renderer must not use `api_key`, `api_key_masked`, or copied JSON editor values.
- The safe public identifier is `consumer_key`; if it is missing, fall back to the display name or a stable local label.

## Compatibility

- Existing multi-key JSON editing remains unchanged.
- Existing command center sections keep their order, with the consumer usage console placed after the handoff kit and before aggregate metrics.
- No backend migration is required.

## Rollback

Revert the added renderer, CSS, and tests. Since no data schema or API behavior changes are expected, rollback is limited to static assets and frontend tests.
