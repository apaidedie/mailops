# Provider capability matrix design

## Boundaries

This is a frontend display adapter over the existing unified mailbox directory payload. The implementation should touch the unified mailbox template, unified mailbox frontend module, i18n strings, CSS, and frontend contract tests. Backend changes should be avoided unless inspection proves the current `/api/mailboxes` payload lacks a required field that is already part of the provider discovery contract.

## Data Flow

`GET /api/mailboxes` remains the only browser data source. The matrix reads:

- `data.provider_context.provider_integration_guide.providers` for provider rows.
- `provider.capabilities` for read mode, dynamic creation, and remote cleanup booleans.
- `provider.active`, `provider.configured`, `provider.readiness_status`, `provider.missing_config`, `provider.required_env`, `provider.optional_env`, and `provider.kind` for status display.
- `provider.health` and `provider.mailbox_directory_filter` for endpoint hints.
- `data.filters.provider` and existing `setUnifiedProviderFilter()` if row interactions filter the directory.

The renderer should no-op when the mount is absent. Loading and error paths should explicitly overwrite the matrix container so old ready rows cannot survive a failed refresh.

## Rendering Shape

Add one mount after `unifiedMailboxProviderContext` and before `unifiedMailboxList`. The container should be a compact panel-like section owned by the page layout, with individual provider rows as repeated lightweight items. Keep table semantics only if mobile wrapping stays clean; a grid/list hybrid is safer for long env keys and endpoints.

Each row should show the provider identity, state badge, missing configuration, and capability chips. Capability labels must come from generic field meaning, not provider-specific copy.

## Compatibility

Do not remove or rename `legacy_bridge`, `gptmail`, `legacy_gptmail`, or `temp_mail` aliases. Do not special-case DuckMail behavior in the matrix. DuckMail should appear correctly because its provider guide entry exposes required env and Mail.tm-compatible capabilities.

Secret handling follows the provider integration guide contract: display secret key names only; never display values. No copy helper is required for this MVP, which keeps the risk surface low.

## Trade-Offs

Using `provider_integration_guide.providers` instead of `provider_diagnostics.providers` keeps the unified mailbox directory aligned with the backend spec that diagnostics in `provider_context` should stay summary-oriented. It also gives the matrix endpoint and deployment metadata without adding a second provider table in JavaScript.

Avoiding a new backend field keeps the slice small. If future UX needs richer per-provider runtime health, that should be a separate backend contract change rather than a browser probe.

## Rollback

The change should be removable by deleting the mount, renderer, CSS selectors, i18n strings, and frontend contract assertions. Since no backend data contract changes are planned, rollback should not affect API clients.
