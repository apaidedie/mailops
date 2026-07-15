# Dynamic temp provider selector audit

## Goal

Keep the temp-mail creation provider selector aligned with the backend provider catalog so installed plugin providers and future temp-mail providers can be selected without editing the static HTML template.

## Requirements

- The temp-mail creation selector may keep built-in HTML options as a startup fallback, but after `/api/providers` loads it must merge temp providers from the catalog into `#tempEmailProviderSelect`.
- The merge must preserve the user's current selection when the selected provider still exists.
- The selector must not add account providers, `auto`, or empty provider names.
- Plugin providers added by the existing plugin manager must not be duplicated when the catalog refreshes.
- Provider labels must come from the catalog when available, with stable fallback text for startup or degraded catalog states.
- The change must not alter backend provider selection priority, provider aliases, external API request fields, or secret handling.

## Acceptance Criteria

- [x] `static/js/main.js` exposes a catalog-driven temp provider selector sync called from `loadMailboxProviderCatalog()` after the catalog cache is refreshed.
- [x] `static/js/features/temp_emails.js` can use catalog labels for display without relying only on static select option text.
- [x] Frontend contract tests prove the temp provider selector is catalog-aware, deduplicates options, preserves selection, and still has static fallback options.
- [x] Existing temp-mail provider, settings, unified mailbox, and external API regression tests continue to pass.

## Notes

- This was found during a provider integration audit: backend discovery is dynamic, while the creation selector still depends on static template entries plus plugin-page refresh behavior.
