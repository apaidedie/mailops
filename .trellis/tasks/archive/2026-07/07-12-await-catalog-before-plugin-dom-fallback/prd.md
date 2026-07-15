# Await catalog before plugin DOM fallback

## Goal

Prevent async catalog re-render from wiping plugin-injected radios/options by awaiting catalog force-refresh first, then re-applying plugin DOM fallback.

## Confirmed Facts

- `loadMailboxProviderCatalog(true)` rewrites Settings radios and temp-email select when the fetch completes.
- Plugin manager injects installed plugin options into those same mounts.
- Current order injects first then fires a non-awaited catalog refresh, so late catalog success can remove plugin-only options that are not yet loaded into the runtime registry.

## Requirements

- Await catalog force-refresh when available.
- Re-run plugin radio/select injection after catalog refresh settles.
- Keep graceful no-op when catalog helper is missing.
- Contract tests assert await + post-refresh reinjection order.

## Acceptance Criteria

- [x] Catalog refresh is awaited before relying on plugin DOM fallback.
- [x] Plugin radios/select reinjected after catalog settles.
- [x] Focused tests + `git diff --check` pass.

## Out Of Scope

- Removing dual DOM injection entirely.
- Changing plugin install/reload backend semantics.
