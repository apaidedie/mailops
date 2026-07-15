# External API consumer usage console

## Goal

Make the external API area operational for real integrations by showing a safe, operator-facing view of each configured API consumer and its current-day usage. The service already supports multiple external API keys and persists daily usage counters; this task turns that data into a readable console in Settings -> API Security.

## Background

- The project goal is a unified mailbox aggregation service with Outlook/IMAP, temporary mailbox providers, extensible provider contracts, and external APIs for other services.
- `/api/settings` already returns `external_api_keys` with safe consumer metadata and today usage fields: `today_total_count`, `today_success_count`, `today_error_count`, and `today_last_used_at`.
- `outlook_web.services.external_api.audit_external_api_access()` records external API usage through `record_external_api_consumer_usage()` when an authenticated consumer calls audited external endpoints.
- The Settings -> API Security page currently exposes a JSON editor for multi-key configuration and an external API command center, but it does not give operators a compact per-consumer usage/status view.

## Requirements

1. Add an External API consumer usage console to the API Security command center.
2. Render only safe fields already exposed by `/api/settings`: consumer name, consumer key, enabled state, pool access, allowed mailbox scope, `last_used_at`, and today usage counters.
3. Do not render plaintext API keys and do not read secret input DOM values such as `settingsExternalApiKey` or the multi-key JSON editor when building the usage console.
4. Show clear status for active/disabled consumers, pool access, scoped/unscoped mailbox access, zero-usage consumers, and consumers with errors today.
5. Keep the UI dense, responsive, and consistent with the existing operational SaaS style in the API Security tab.
6. Preserve current save/edit behavior for the multi-key JSON editor.

## Acceptance Criteria

- [x] Settings -> API Security shows a consumer usage section inside the external API command center when settings are loaded.
- [x] Empty state explains that no multi-key consumers are configured without suggesting that a plaintext key is visible.
- [x] The rendered console includes per-consumer counts for total, success, error, and last use when data exists.
- [x] Disabled and erroring consumers are visually distinguishable through semantic text/classes, not color alone.
- [x] Frontend contract tests cover the renderer, the safe field policy, and placement within the command center.
- [x] `node --check static/js/main.js`, focused frontend tests, and whitespace checks pass.

## Out Of Scope

- New backend database schema or new settings endpoint unless inspection proves the existing fields are insufficient.
- Displaying historical charts beyond today's summary.
- Changing API authentication behavior or rotating keys.
