# Frontend integration manifest starter

## Goal

Make the Settings API Security starter kit consume the new backend `integration_manifest` contract so the UI and external discovery payloads share the same API key placeholder, endpoint sequence, provider request fields, and secret-safe env/config hints.

## Confirmed Facts

- The backend now returns top-level `integration_manifest` from authenticated `/api/providers`, external `/api/external/providers`, external `/api/external/capabilities`, and OpenAPI `x-capabilities`.
- `static/js/main.js` currently caches `provider_integration_guide` and generates the starter snippets from guide providers plus locally derived auth and endpoint defaults.
- Existing frontend tests already assert the starter kit is secret-safe and does not read real secret inputs.
- The change should preserve the existing starter modes: curl, JavaScript, Python, and env/config hints.

## Requirements

- Cache `integration_manifest` from `/api/providers` in `static/js/main.js` alongside the existing guide cache.
- Prefer manifest data for starter snippets: auth header/placeholder, discovery endpoint sequence, provider env hints, and provider request fields.
- Keep `provider_integration_guide` as a fallback for older payloads or partial manifest data.
- Do not read or expose real API key, DuckMail bearer token, provider password, JWT, consumer key, task token, or refresh token values from form inputs.
- Keep UI copy and layout stable unless the manifest data enables clearer labels.
- Add or update frontend tests to assert `main.js` uses `integration_manifest`, still supports guide fallback, and keeps secret values out of snippets.

## Acceptance Criteria

- `static/js/main.js` stores `/api/providers` `integration_manifest` in a cache and uses it in starter snippet helpers.
- Starter snippets use `<your-api-key>` from manifest auth when available.
- Env/config starter snippets use manifest provider hints with empty values for secret keys and non-secret defaults for base URLs.
- Existing provider guide rendering continues to work.
- `node --check static/js/main.js` passes.
- Relevant frontend tests pass.
- Debug log and DuckMail token scans pass.

## Out of Scope

- Rebuilding the full Settings visual design.
- Adding new backend fields.
- Changing API authentication or provider selection runtime behavior.
