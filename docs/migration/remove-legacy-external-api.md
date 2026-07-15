# Migration: Remove legacy `/api/external/*` routes

## What changed

Outlook Email Plus external automation APIs are **v1-only**:

| Before | After |
|--------|--------|
| `/api/external/*` (legacy alias) | **Removed** (404) |
| `/api/v1/external/*` (canonical) | **Required** |

Discovery payloads now report:

- `compatibility.legacy_supported = false`
- `compatibility.legacy_endpoints = {}`
- `compatibility.aliases = {}`
- `compatibility.removed_legacy_prefix = "/api/external"`
- `compatibility.migration_doc = "docs/migration/remove-legacy-external-api.md"`

OpenAPI `paths` and `x-legacy-endpoints` no longer advertise legacy operations.

## Who must migrate

Any registration worker, browser extension, script, or SDK that still calls:

```text
/api/external/...
```

## How to migrate

1. Prefer discovery: `GET /api/v1/external/capabilities` (or `integration-bundle`) and copy paths from `endpoints` / `quickstart`.
2. Mechanical replace: `/api/external` → `/api/v1/external` on every external automation call.
3. Keep `X-API-Key` auth unchanged.
4. Re-run read-only smoke: `python scripts/external_api_smoke.py --base-url <url>`.

## Verification

```bash
# legacy must 404
curl -s -o /dev/null -w "%{http_code}" -H "X-API-Key: $KEY" "$BASE/api/external/health"

# v1 must 200
curl -s -o /dev/null -w "%{http_code}" -H "X-API-Key: $KEY" "$BASE/api/v1/external/health"
```

## Rollback

Restore the pre-W2 commit that dual-mounted routes via `add_external_api_url_rule` (legacy + v1). Not recommended for new deployments.
