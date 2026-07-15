# External API Quickstart Contract Design

## Scope

This task adds a compact `quickstart` projection to the existing external integration manifest. It does not add new routes, change auth, change provider selection semantics, or alter runtime mailbox actions.

## Backend Design

`outlook_web.services.provider_catalog` owns a helper that builds the quickstart object from the same endpoint map, selection policy, and manifest workflow keys used by `get_external_integration_manifest()`.

`integration_manifest.quickstart` is the source of truth. `get_external_api_capabilities_contract()`, `/api/external/providers`, and authenticated `/api/providers` expose `quickstart` by copying it from the manifest, not by rebuilding it in controllers.

The quickstart object is versioned and secret-free. It includes auth placeholder metadata, the recommended discovery sequence, external endpoint paths, selector field names and allowed values, minimal request examples for mailbox browsing, pool claim, and task temp mailbox apply, plus workflow keys that point back to the full manifest.

## OpenAPI Design

OpenAPI adds `IntegrationQuickstart`, nested auth, sequence, selector, and request example schemas. `CapabilitiesData`, `ProviderCatalogData`, and `IntegrationManifest` reference the same schema.

## Compatibility

The change is additive. Existing clients that ignore unknown fields continue to work, while new clients can start from `quickstart` and progressively read the full manifest.

## Risk Controls

Tests assert shared object equality, provider-selector derivation, schema exposure, and secret-safety under configured provider secret env values. The implementation avoids provider-name branches and network probes.
