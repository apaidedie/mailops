# External API CORS policy

## Goal

Make the external API safely usable from explicitly approved browser applications while preserving the existing Chrome/Edge extension integration and keeping all internal admin/session endpoints outside the CORS boundary. The policy must be default-deny for ordinary web origins, machine-discoverable, and easy to configure in containers.

## Confirmed Facts

- CORS is currently configured inline in `outlook_web.app.create_app()`.
- Only origins matching `chrome-extension://.*` are allowed.
- CORS is scoped to `/api/external/*` and `/api/v1/external/*`; internal `/api/*` routes remain same-origin only.
- Allowed methods are GET/POST/OPTIONS, allowed headers are Content-Type/X-API-Key, and credentials are disabled.
- No environment setting or discovery/readiness field currently describes browser-origin access.
- External capabilities, readiness, and integration bundle contracts are owned by `outlook_web.services.provider_catalog`.

## Requirements

- Add `EXTERNAL_API_CORS_ORIGINS` as a comma/newline-separated exact allowlist for `http://` and `https://` origins.
- Add `EXTERNAL_API_CORS_ALLOW_CHROME_EXTENSION`, defaulting to true for backward compatibility.
- Normalize trailing slashes, preserve ports, deduplicate origins, and reject wildcard, path, query, fragment, user-info, non-HTTP schemes, and malformed entries.
- Invalid entries must never become active origins. Expose only an invalid entry count, not the raw malformed values, in discovery/readiness.
- Keep `supports_credentials=false`; never combine credentialed CORS with API-key browser calls.
- Keep CORS scoped only to canonical and legacy external API paths.
- Allow `Content-Type`, `X-API-Key`, `X-Request-Id`, and `X-Trace-Id`; expose `X-Trace-Id`; use a bounded preflight max age.
- Move CORS policy construction/registration out of `app.py` into a dedicated module.
- Add a secret-safe CORS policy object to external capabilities and external API readiness, which automatically flows into the integration bundle.
- Preserve server-to-server API availability when browser CORS is disabled or invalid; CORS status must not degrade general external API readiness.
- Add focused config, preflight, scope, capabilities, readiness, compatibility, and secret-safety tests.
- Document the environment keys and browser integration guidance in `.env.example`, runtime readiness, and external integration quickstart.
- Extend the local readiness contract and mark explicit CORS configuration complete in the project map.

## Acceptance Criteria

- [ ] Default configuration still allows `chrome-extension://` origins and denies ordinary web origins.
- [ ] A configured exact HTTPS/HTTP origin receives CORS headers on canonical and legacy external endpoints.
- [ ] Wildcards and malformed origins are ignored and reported only as `invalid_origin_count`.
- [ ] Disabling extension support removes Chrome extension CORS access without affecting configured web origins.
- [ ] Internal API routes never receive external CORS headers.
- [ ] Capabilities/readiness expose a stable safe CORS policy contract.
- [ ] Existing API-key auth remains required; CORS does not create an authentication bypass.
- [ ] Focused tests, external API/readiness regressions, readiness gate, formatting/type checks, and `git diff --check` pass.

## Out Of Scope

- Allowing wildcard browser origins.
- Supporting cookies or session credentials across origins.
- Adding per-consumer/database-managed CORS origins in this task.
- Changing external API authentication or rate limiting.
- Applying CORS to admin/session endpoints.

## Notes

- Keep `prd.md` focused on requirements, constraints, and acceptance criteria.
- Lightweight tasks can remain PRD-only.
- For complex tasks, add `design.md` for technical design and `implement.md` for execution planning before `task.py start`.
