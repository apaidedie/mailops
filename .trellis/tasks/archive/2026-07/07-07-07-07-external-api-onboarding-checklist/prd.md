# External API onboarding checklist

## Goal

Make first-run external API readiness obvious in the Settings API Security command center so an admin can tell why external calls are rejected before trying to integrate another service.

## Confirmed Facts

- `templates/index.html` renders `#externalApiCommandCenter` before the external API key fields.
- `static/js/main.js` already renders external endpoints, starter snippets, workflow playbooks, provider recipes, and status metrics.
- The command center must remain a read-only display over authenticated settings data and provider discovery caches.
- Current frontend specs forbid reading real API key, provider token, masked placeholder, or provider-specific secret inputs inside command-center helpers.
- Provider selection, endpoint paths, source priority, and secret behavior are already covered by existing frontend contracts and must not be changed.

## Requirements

- Add a compact onboarding checklist inside the existing External API command center.
- The checklist must use settings payload fields and provider discovery caches only.
- The checklist must show API-key readiness, multi-key posture, External Pool state, Provider catalog state, and discovery endpoint availability.
- When no API key is configured, the checklist must explain that the admin should generate an API key and save settings before external services call the API.
- The checklist must keep external discovery endpoints visible even when API-key or provider-catalog setup is incomplete.
- The checklist must not expose, copy, log, or read real API keys, masked API-key values, DuckMail bearer tokens, provider JWTs, passwords, consumer keys, task tokens, or provider credential input elements.
- The change must keep the existing command center, starter snippets, provider recipes, workflow playbooks, and endpoint rows intact.
- The layout must wrap long labels and endpoint text without creating mobile overflow.

## Acceptance Criteria

- Frontend contract tests assert onboarding helper and renderer names exist.
- Frontend contract tests assert the command center renders the onboarding checklist before the status metrics.
- Frontend contract tests assert the missing-key guidance text exists in the production script and translations.
- Frontend contract tests assert onboarding helper slices do not reference API-key or provider-secret input IDs.
- CSS contract tests assert the new checklist hooks and mobile-safe wrapping styles exist.
- `node --check static/js/main.js`, focused frontend tests, and `git diff --check` pass.
