# Prefer settings snapshot over pending when temp-mail radios unbound

## Problem

`applyTempMailSettingsSelection()` always writes the canonicalized pending provider
on the mount, even when radios are not bound. `collectTempMailSettingsPayload()` then
preferred pending over snapshot, so a global save from Basic could still rewrite
stored `custom_domain_temp_mail` to `legacy_bridge` without the user opening temp-mail.

## Goal

1. When radios are unbound, collect from snapshot before pending/default.
2. When radios are bound, checked → pending → snapshot → default.
3. Keep operator default as last resort only.

## Acceptance Criteria

- [x] Unbound path prefers raw snapshot over pending/default
- [x] Bound path still prefers live selection/pending
- [x] Focused tests + node --check + git diff --check pass
