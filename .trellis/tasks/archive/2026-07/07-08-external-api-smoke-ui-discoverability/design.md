# External API Smoke UI Discoverability Design

## Architecture

The smoke-check panel is a read-only display and copy adapter inside `static/js/main.js`. It uses the same command-center render path as existing Quickstart and workflow playbooks.

No backend endpoint is required. The browser will not execute the smoke checker or call external discovery endpoints on behalf of the user. It only renders a copyable command and coverage list.

## UI Composition

Add a compact section after the onboarding checklist and before metrics/quickstart. The panel contains:

- a short title and status line for deployment verification,
- coverage chips for health, capabilities, providers, mailboxes, and OpenAPI,
- a preformatted command block,
- a copy button.

The visual language should match the existing command center: calm operational density, bordered surfaces, small headings, wrapped code, and stable responsive grid behavior.

## Data and Secret Safety

The command uses placeholders:

```bash
MAILOPS_API_KEY=<your-api-key> python scripts/external_api_smoke.py --base-url <your-base-url>
```

`<your-base-url>` can be a placeholder or derived from `window.location.origin` only if that value is not a secret. API keys, provider tokens, masked values, and settings input values must never be read or copied.

## Compatibility

Existing command center functions remain. This is additive and uses new helper names so frontend contract tests can enforce the boundary.

## Rollback

Remove the smoke panel helper/render/copy functions, remove the inserted render call and event handler, remove CSS hooks, and revert tests/spec updates.
