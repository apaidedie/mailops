# External integration starter kit

## Goal

Make Settings -> API Security more useful for external projects by adding a secret-safe integration starter kit to the existing external API command center.

An administrator should be able to copy a ready-to-adapt curl, JavaScript, Python, or environment/config starter snippet that discovers capabilities, reads provider policy, and points callers to the unified mailbox directory without exposing real API keys or provider secrets.

## Requirements

- Extend the existing external API command center instead of adding another standalone entry point.
- Provide multiple starter snippet modes for external consumers: curl discovery, JavaScript fetch, Python requests, and provider environment/config hints.
- Build snippets from existing command-center helpers and provider discovery caches, especially endpoint map, source priority, provider route mode, and provider integration guide data.
- Keep all snippets secret-safe. Use placeholders such as `<your-api-key>` and show provider secret key names only with empty values; never read API key or provider credential input values.
- Preserve current external API behavior, provider selection priority, request fields, provider aliases, OpenAPI output, and backend contracts.
- Keep the UI compact, operational, responsive, and aligned with the current vanilla JS/CSS design system.
- Reuse existing copy helpers and event delegation patterns.

## Acceptance Criteria

- `templates/index.html` exposes a starter-kit mount/control area within the existing external API command center markup path or render output.
- `static/js/main.js` defines a starter-kit snippet builder that supports curl, JavaScript, Python, and env/config modes and is rendered by `renderExternalApiCommandCenter()`.
- The copy action copies the currently selected starter snippet, not only the curl command.
- The starter-kit builder does not reference secret input IDs such as `settingsExternalApiKey`, `settingsExternalApiKeysJson`, provider token/key inputs, or masked placeholders.
- Snippets include stable external discovery endpoints and provider selection hints from discovery data; they continue to work if a future provider is added to the catalog.
- `static/css/main.css` defines responsive styles for the starter-kit controls and code block with long-text wrapping.
- `static/js/i18n.js` includes the new visible copy in Chinese and English.
- Frontend contract tests assert mounts/render helpers, supported modes, copy behavior, secret-safety constraints, CSS hooks, and translations.
- Existing external API/provider/settings tests continue to pass.
- Static scans find no production `console.log`/`console.debug` and no committed DuckMail bearer token value.

## Out of Scope

- Adding a generated SDK package, changing OpenAPI schemas, or adding new external API endpoints.
- Reading, copying, logging, or rendering real API keys, DuckMail tokens, provider JWTs, passwords, consumer keys, or task tokens.
- Redesigning the whole Settings page or introducing a frontend framework/component library.
