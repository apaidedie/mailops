# Catalog-driven pool admin provider filter

## Goal

Replace hard-coded `#poolAdminProviderFilter` options with catalog-driven values so pool admin type filtering stays aligned with live mailbox providers (account + temp, including plugins/aliases).

## Confirmed Facts

- Template hard-codes only `outlook`, `imap`, `custom`, `cloudflare_temp_mail`.
- `loadPoolAdmin()` reads `#poolAdminProviderFilter` and sends `provider` to `GET /api/pool-admin/accounts`.
- Group filter already uses dynamic `ensurePoolAdminGroupOptions()` from `/api/groups`.
- `/api/providers` exposes `mailbox_providers` with `provider`, `label`, `kind`.
- `loadMailboxProviderCatalog()` already caches catalog in main.js.
- Pool accounts can use account providers and some temp providers (e.g. CF, gptmail).

## Requirements

- Populate `#poolAdminProviderFilter` from provider catalog after catalog load / on pool-admin open.
- Keep empty value option as “所有类型”.
- Preserve current selection when re-rendering when still valid.
- Do not hard-code built-in provider option lists in template.
- Prefer labels from catalog; fall back to provider key.
- Exclude pure selector tokens like `auto` from admin filter options.
- Update frontend contract tests.

## Acceptance Criteria

- [x] Template `#poolAdminProviderFilter` has no hard-coded provider option values beyond the empty “所有类型” placeholder.
- [x] `pool_admin.js` (or shared helper) fills options from `/api/providers` / catalog cache.
- [x] Options include current catalog providers (account + temp) with labels.
- [x] Existing provider filter query param behavior still works.
- [x] Focused frontend tests + `git diff --check` pass.

## Out Of Scope

- Changing pool-admin backend filter semantics.
- Active-providers textarea autocomplete.
- Status/in-pool filter redesign.
