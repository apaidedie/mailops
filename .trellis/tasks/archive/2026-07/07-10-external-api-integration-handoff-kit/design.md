# Design

## Boundaries

This is a frontend-only enhancement over existing discovery contracts. The backend Integration Bundle remains the canonical external payload. The admin UI creates a local handoff document from already-loaded, secret-safe admin/discovery caches and placeholder auth only.

## Data Sources

- `getExternalIntegrationManifest()` supplies auth placeholder, discovery sequence, workflows, providers, docs, and endpoint maps.
- `getExternalIntegrationQuickstart()` supplies recommended sequence, selector fields, and request examples.
- `getExternalApiBundleEndpointDescriptor()` supplies canonical and legacy bundle paths.
- `getExternalApiSmokeCommand()` supplies the read-only smoke command.
- `getExternalApiActionPlan(settings, state, providerSummary)` supplies the local triage/action-plan projection.
- `getExternalApiMailboxSessionRequestExamples()` supplies session start/read/close examples.
- `getExternalApiStarterBaseUrl()` and `getExternalApiCommandUrl()` supply current-origin URLs without reading credentials.

## UI Shape

Add a compact handoff kit panel to the command center, near the Integration Bundle launchpad. It should read as a developer handoff card, not a marketing hero. Use the existing external-api prefix and operational card styling. The panel contains a short explanation, compact chips for what the handoff includes, a preview code block, and a copy button.

The copied document is plaintext Markdown-like content, optimized for pasting into another project issue, README, `.env` notes, or developer chat. It uses placeholders only:

- `X-API-Key: <your-api-key>`
- `<your-base-url>` when origin is unavailable
- `<caller-id>`, `<task-id>`, `<claim-token>`, `<task-token>`, `<provider-name>`, and similar non-secret example handles

## Secret Safety

The handoff builder must not query DOM inputs or settings credential fields. It only reads normalized caches and helper outputs that already use placeholders. It should sanitize text by construction: no API key value interpolation, no masked key reuse, no provider token value, and no localStorage persistence.

## Compatibility

Existing render order remains: onboarding checklist, smoke-check panel, Integration Bundle launchpad, then the new handoff kit, then metrics/readiness/quickstart/session/workflows. This keeps the bundle as the primary machine-readable starting point and makes the handoff kit the human-copyable companion.

## Visual Direction

Use the UI skills as a light guide: developer-tool clarity, strong hierarchy, dark/light compatibility, subtle hover/focus states, compact cards, and robust wrapping. Do not import fonts, icons, GSAP, or new dependencies.
