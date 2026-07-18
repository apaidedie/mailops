# Provider preflight console design

## Boundaries

This is a frontend/admin-console task over the existing authenticated preflight endpoint. Backend behavior stays unchanged. The owner of provider readiness remains `mailops.services.provider_catalog`; the UI only fetches and formats the returned `provider_preflight` object.

The panel lives inside Settings -> API Security -> `#providerWorkbench`, near the existing provider overview and contract status. It must compose with the existing `/api/providers` cache, provider workbench renderer, and language-change/render hooks.

## Data Flow

Settings load calls `/api/settings`, then `/api/providers`, then the new preflight loader calls `/api/providers/preflight` with no query for local-only readiness. Manual probe calls the same loader with `probe_network=true`.

`loadProviderPreflightSnapshot(forceRefresh, probeNetwork)` owns fetch, pending/error state, cache replacement, and `renderProviderWorkbench(...)` refresh. `providerPreflightCache` stores only the secret-free runtime payload. `providerPreflightState` tracks `idle`, `loading`, `ready`, `probing`, or `error` plus last probe mode.

## UI Shape

The panel has:

- compact summary counters: total, ready, needs-config, inactive, probed, failed probes;
- a clear status badge: ready, needs config, degraded, error, loading;
- a manual explicit-probe button;
- a dense provider list with provider label/key, kind, local status, missing config key names, probe status, and small endpoint hint.

The panel uses stable `provider-preflight-*` CSS hooks and existing token variables. It keeps cards shallow, uses grids that collapse to one column on mobile, and wraps long provider keys/config keys/endpoints.

## Safety

The UI must not read Settings credential input IDs or form values. It must not render raw secrets. It should render key names such as `DUCKMAIL_BEARER_TOKEN` or `duckmail_bearer_token` only when they arrive as configuration key names in the secret-free preflight payload.

## Compatibility

If `/api/providers/preflight` is unavailable or fails, existing Settings and provider workbench surfaces remain visible. The preflight panel shows a degraded/error state and offers retry. The existing single-provider health buttons remain unchanged.
