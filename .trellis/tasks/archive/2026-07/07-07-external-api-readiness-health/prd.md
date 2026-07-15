# External API readiness health summary

## Goal

Make `GET /api/external/health` more useful for external integrators by returning a compact, secret-free readiness summary that answers whether the instance is ready for discovery, provider-backed temp mail, and pool workflows.

## Requirements

- Keep the existing endpoint path, API key authentication, response envelope, and existing top-level health fields backward compatible.
- Add a `readiness` object to the health data with compact machine-readable status for overall external API readiness, discovery endpoints, provider local readiness, pool availability, and task temp-mail availability.
- Build readiness from existing provider catalog/capability helpers so it cannot drift from `/api/external/capabilities` or `/api/external/providers`.
- Do not call upstream provider networks from `/api/external/health`; keep network probing limited to the existing cached instance probe and explicit provider health probes.
- Never expose API key values, provider secrets, bearer tokens, passwords, refresh tokens, task tokens, or consumer keys.

## Acceptance Criteria

- [x] `GET /api/external/health` still returns all previous fields and includes `readiness`.
- [x] `readiness` reports external API, provider, pool, task temp-mail, and discovery status using stable string keys.
- [x] Multi-key consumers without pool access see pool readiness as restricted without affecting provider or discovery readiness.
- [x] OpenAPI `HealthData` documents the new `readiness` object.
- [x] Focused external API tests pass.

## Notes

- Lightweight task; PRD-only is sufficient.
