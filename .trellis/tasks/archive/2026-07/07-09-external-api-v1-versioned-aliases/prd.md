# External API v1 versioned aliases

## Goal

Add a stable, versioned external API entrypoint under `/api/v1/external/*` while preserving every existing `/api/external/*` route as a backwards-compatible legacy path. This moves the project toward a professional third-party integration surface without forcing current clients, UI panels, smoke scripts, or docs to migrate in one breaking step.

## Background

- The project goal is to become a unified Outlook/IMAP/temp-mail aggregation service with durable external APIs for other services.
- `docs/项目地图.md` lists API versioning as a high-priority item: move external APIs from `/api/external/*` toward `/api/v1/external/*` to avoid future breaking changes.
- Existing discovery, OpenAPI, quickstart, Settings UI, and tests currently use `/api/external/*` paths.
- External routes are split across `mailops/routes/system.py`, `mailops/routes/emails.py`, `mailops/routes/external_pool.py`, and `mailops/routes/external_temp_emails.py`.
- The safest first step is non-destructive aliasing: mount the same controller handlers at both legacy and v1 paths, then make discovery advertise v1 as canonical with legacy compatibility metadata.

## Requirements

- Add `/api/v1/external/*` aliases for the complete current external API surface:
  - `GET /health`
  - `GET /capabilities`
  - `GET /openapi.json`
  - `GET /account-status`
  - `GET /mailboxes`
  - `GET /providers`
  - `GET /providers/preflight`
  - `GET /providers/<kind>/<provider>/health`
  - mailbox session `POST /mailbox-sessions/start|read|close`
  - message read endpoints including detail/raw/probe/wait/verification paths
  - pool claim/release/complete/stats endpoints
  - task temp-mail apply/finish endpoints
- Keep all existing `/api/external/*` routes fully operational and protected by the same API-key auth, guards, rate limits, CSRF exemptions, and audit behavior.
- Avoid duplicating controller business logic. Alias registration should reuse the same view functions.
- Make discovery payloads expose the v1 endpoint map as canonical while preserving legacy endpoint metadata so existing clients can still discover compatibility paths.
- Ensure OpenAPI exposes canonical `/api/v1/external/*` paths and also signals legacy `/api/external/*` compatibility in a machine-readable extension.
- Update smoke tooling/tests so clients can validate either canonical v1 discovery or legacy compatibility without weakening secret-safety checks.
- Do not rename internal settings keys, feature flags, provider names, or API-key headers.
- Do not remove or redirect legacy routes in this task.

## Acceptance Criteria

- [ ] A focused route test proves representative v1 aliases work with the same API-key auth as legacy paths.
- [ ] The full external endpoint map in capabilities/integration manifest/quickstart uses `/api/v1/external/*` as canonical paths.
- [ ] Discovery payloads include a legacy compatibility map for `/api/external/*` paths.
- [ ] OpenAPI contains canonical v1 paths for discovery, mailbox session, message read, pool, and task temp-mail endpoints.
- [ ] OpenAPI exposes legacy compatibility metadata without duplicating every operation body by hand.
- [ ] Existing legacy-path tests remain green, proving backwards compatibility.
- [ ] Smoke contract validation passes after being updated for canonical v1 + legacy compatibility.
- [ ] Backend spec documents the versioning contract and the forbidden pattern of creating a second controller implementation.

## Notes

- This task intentionally does not switch the authenticated Settings UI or all docs to v1 in one pass. After discovery exposes canonical v1, UI/docs can follow gradually using the same endpoint map.
