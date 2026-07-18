# Provider readiness preflight contract design

## Boundaries

`mailops.services.provider_catalog` remains the owner of provider discovery and readiness projection. Controllers should only parse `probe_network`, call the service, wrap the result, and audit external access. The single-provider health contract continues to own local readiness and optional upstream probing. The new preflight helper composes those existing rows into a batch result.

## API shape

Admin route: `GET /api/providers/preflight` returns `{success: true, provider_preflight: ...}` and is protected by the existing login guard.

External route: `GET /api/external/providers/preflight` returns the same preflight object as `data` through the existing external envelope and is protected by the API key guard and external API guards.

Query fields: `probe_network` is optional and false by default. The initial implementation probes every locally ready temp provider only when true; account providers stay local-only because existing Graph/IMAP account probes are account-specific, not provider-wide.

## Response shape

The preflight object has `version`, `status`, `scope`, `summary`, `issues`, `defaults`, `filter`, `endpoints`, `providers`, `readiness_summary`, and `documentation`. Provider rows include local readiness, missing config names, support flags, endpoint hints, contract validation, and a probe object. Secret key names are allowed where already exposed by the discovery contract, but secret values are not.

## Discovery integration

The endpoint map gains `provider_preflight`. Capabilities, provider integration guide, integration manifest discovery endpoints, quickstart endpoints and requests, provider discovery payloads, mailbox directory provider context discovery, and OpenAPI paths must all derive that path from the same provider-catalog endpoint map.

## Compatibility

Existing `provider_health` remains unchanged. Existing tests that assert the provider health endpoint path continue to pass. The preflight endpoint is additive.

## Safety

Default local-only preflight must not instantiate temp-mail providers. Explicit network probe uses `get_mailbox_provider_health(..., probe_network=True)`, so existing redaction and provider readiness checks are reused.
