# Catalog-driven pool default datalist

## Goal

Replace the hard-coded Settings `#poolDefaultProviderOptions` suggestions with values from `/api/providers` selection policy so pool default provider options stay aligned with the live catalog (including plugins / aliases) without template drift.

## Confirmed Facts

- Settings API Security keeps free-text input `#poolDefaultProvider` with `list="poolDefaultProviderOptions"`.
- Template currently hard-codes options: `auto`, `outlook`, `gmail`, `custom`, `imap`, `mail_tm`, `duckmail`, `tempmail_lol`, `emailnator`, `cloudflare_temp_mail`, `gptmail`.
- Catalog selection policy already exposes `scopes.pool_claim_default.allowed_values` (and matching `explicit_pool_claim.allowed_values`) including account providers, temp providers, aliases, and `auto`.
- Frontend already loads `/api/providers` via `loadMailboxProviderCatalog()` and caches catalog/diagnostics/deployment/guide/manifest.
- Setting key remains `pool_default_provider`; backend validation already rejects invalid providers.
- Prior schema-complete task explicitly deferred this follow-up.

## Requirements

- Populate `#poolDefaultProviderOptions` from catalog selection policy after provider catalog load (and on language/catalog refresh if already loaded).
- Prefer `selection_policy.scopes.pool_claim_default.allowed_values`; fall back to `explicit_pool_claim.allowed_values` when needed.
- Always include `auto` first when missing from the list.
- Keep free-text input behavior and existing save/load of `pool_default_provider`.
- Do not hard-code built-in provider lists in the template or renderer.
- Update frontend contract tests for the dynamic datalist path.

## Acceptance Criteria

- [x] Template `#poolDefaultProviderOptions` no longer hard-codes provider option values (empty/loading-safe mount is OK).
- [x] `main.js` fills datalist options from `/api/providers` selection policy allowed values.
- [x] Options include at least `auto` plus current catalog pool-claim allowed providers.
- [x] Existing `#poolDefaultProvider` save/load still works.
- [x] Focused frontend tests + `git diff --check` pass.


## Out Of Scope

- Changing backend validation rules for `pool_default_provider`.
- Replacing free-text input with a strict select.
- Catalog-driving pool admin filter dropdowns (separate surface).
- Active mailbox providers textarea autocomplete.
