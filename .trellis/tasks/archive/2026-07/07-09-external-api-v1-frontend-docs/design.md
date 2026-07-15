# External API v1 frontend docs canonical Design

## Architecture

This task changes only display/copy surfaces. Backend route aliases, provider catalog generation, OpenAPI generation, API-key auth, and external guards stay unchanged.

The frontend command center should continue consuming backend discovery data first:

- `integration_manifest.discovery.endpoints`
- `provider_integration_guide.endpoints`
- command-center endpoint cache derived from authenticated provider discovery

Fallback literals exist only for degraded or partial-discovery states. Those fallback literals must now use `/api/v1/external/*` because they are what new operators see when catalog data is missing.

## Canonical vs Legacy Copy

- Canonical copy: default snippets, smoke commands, README examples, quickstart examples, and path-prefix summaries use `/api/v1/external/*`.
- Legacy copy: only compatibility notes, `legacy_endpoint` fields, compatibility metadata, or tests intentionally exercising backwards compatibility use `/api/external/*`.

The UI should not add a second switch for legacy paths. Compatibility is discoverable from backend metadata and documentation text; the operator's primary copy path remains v1.

## UI Constraints

The Settings command center is a dense operational panel built with Flask templates, plain JavaScript, and CSS. This task does not change layout, add animations, or introduce a component library. Existing copy buttons and code panels remain the interaction model.

## Documentation Strategy

Docs should be updated in place:

- `README.md` and `README.en.md`: external integration section and provider-selection paragraphs.
- `docs/external-integration-quickstart.md`: all example URLs and lifecycle endpoint bullets.
- `docs/项目地图.md`: mark API versioning complete.

Avoid rewriting unrelated historical changelog entries or old test fixtures whose purpose is legacy compatibility.

## Rollback

Rollback is a normal Git revert of this task. No migration or setting change is involved.
