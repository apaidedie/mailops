# Schema-complete specialized temp-provider panels

## Goal

Finish the dual-path temp-mail settings UI: represent legacy bridge and Cloudflare fields/actions through catalog `settings_ui` / `config_schema`, so Settings save/load/render no longer depend on hard-coded DOM IDs or dedicated static panels.

## Confirmed Facts

- Selector rendering is already catalog-driven (`settings_ui` from prior task).
- `templates/index.html` still mounts `#gptmailConfigPanel` and `#cfWorkerConfigPanel` with fixed field IDs.
- `collectTempMailSettingsPayload()` and `loadSettings()` always read hard-coded bridge/CF inputs, then also call schema collectors.
- `legacy_bridge` / `cloudflare_temp_mail` catalog contracts expose settings keys but lack `config_schema.fields`.
- CF domain sync uses `POST /api/settings/cf-worker-sync-domains` and updates readonly domain fields.
- Secret masking rules already exist for `temp_mail_api_key` and `cf_worker_admin_key`.
- Plugin path and duckmail/emailnator/tempmail_lol schema panels must remain unchanged.

## Requirements

- Catalog exposes complete editable field metadata for legacy bridge and Cloudflare, including JSON and readonly fields.
- Catalog exposes an action contract for CF domain sync (method, endpoint, labels, result mapping) without hardcoding the action only in frontend provider-name branches.
- Settings UI renders bridge and Cloudflare through the generic schema panel path (`settings_ui.panel=schema` or equivalent generic mode).
- Remove reliance on dedicated static field IDs for save/load; single collector/loader path owns temp provider settings values.
- Preserve secret masking / empty-secret ignore / masked-value unchanged semantics.
- Preserve CF sync behavior and readonly domain reload after sync.
- Keep aliases (`custom_domain_temp_mail` → bridge family) and plugin panel path intact.
- Update backend contract tests, frontend contract tests, and desktop/mobile Settings visual checks.

## Acceptance Criteria

- [x] `legacy_bridge` and `cloudflare_temp_mail` catalog entries include complete `configuration.config_schema.fields` and matching `settings_ui.fields`.
- [x] Cloudflare catalog entry includes a settings action for domain sync mapped to the existing API.
- [x] Static specialized field panels are no longer required for rendering/saving bridge and Cloudflare settings.
- [x] `collectTempMailSettingsPayload` / `loadSettings` no longer hard-code bridge/CF field ID lists for value transfer.
- [x] Secrets remain masked and empty secret inputs do not clear stored values.
- [x] CF sync still updates domain/default domain fields and keeps them readonly.
- [x] Focused backend/frontend tests, readiness, `git diff --check`, and desktop/mobile screenshots pass.


## Out Of Scope

- Replacing the entire Settings page architecture.
- Migrating plugin manager UI.
- Changing CF Worker or bridge upstream APIs.
- Fully removing plugin dedicated panel path.
- Catalog-driven pool default datalist (separate follow-up).
