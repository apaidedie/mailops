# Track plugin list loaded state for ensureLoaded

## Goal

`PluginManager.ensureLoaded()` must treat a successful empty plugin list as loaded, and coalesce concurrent ensure/load calls, so zero-plugin installs do not refetch `/api/plugins` on every Settings open.

## Evidence

- Current `ensureLoaded` only skips when `_plugins.length > 0`.
- Empty successful load still re-hits `/api/plugins` on each `showSettingsModal`.
- Concurrent Settings open + temp-mail tab can start parallel loads.

## Requirements

- Track `_pluginsLoaded` (or equivalent) set true after successful list fetch.
- On load failure, leave unloaded so retry is possible.
- Coalesce in-flight load promise.
- Contract tests assert markers.

## Acceptance Criteria

- [x] Successful empty list counts as loaded.
- [x] Concurrent ensureLoaded shares one in-flight request.
- [x] Focused tests + `git diff --check` pass.
