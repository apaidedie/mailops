# Unified Mailbox Provider Readiness Design

## Scope

This task adds an inventory-aware readiness projection to the existing unified mailbox directory contract. It does not add a new provider registry, change provider selection, or probe upstream services.

## Backend Design

`mailops.services.provider_catalog` owns a new helper that projects readiness from existing `provider_context` inputs: provider diagnostics, provider integration guide, selection policy, defaults, discovery endpoints, and a lightweight mailbox inventory summary passed by `mailbox_catalog`.

The helper returns `readiness_summary` with `version=1`, `overall_status`, `totals`, `issues`, `source_priority`, `provider_selector_fields`, `endpoints`, and `providers`. Per-provider rows are compact and secret-free: `kind`, `provider`, `label`, `active`, `configured`, `readiness_status`, `mailbox_count`, `account_count`, `temp_count`, `can_dynamic_create`, `requires_pool_inventory`, `read_capability`, `missing_config_count`, and endpoint hints.

`list_unified_mailboxes()` already loads mailbox items before filtering. It will compute provider inventory from the account-scoped item list, before user filter narrowing, and pass that inventory into `get_mailbox_directory_provider_context()`. This makes readiness describe the available directory scope rather than only the current filter result.

## Frontend Design

`static/js/features/mailboxes.js` will consume `providerContext.readiness_summary` inside the existing provider-context band and command center. The UI should show a compact status, inventory totals, issue counts, and a few provider rows. It remains a display adapter over backend data and does not define provider-specific behavior.

The design direction is a dense operational dashboard: restrained colors, stable cards, wrapped long paths, no new decorative graphics, and no provider-specific copy branches.

## OpenAPI Design

`MailboxProviderContext` gains a required `readiness_summary` field referencing a new `MailboxProviderReadinessSummary` schema. Nested provider rows get a typed schema with flexible extension fields kept out unless needed.

## Compatibility

Existing clients that ignore unknown fields continue to work. Existing UI fallbacks remain in place if `readiness_summary` is absent from older payloads.

## Risk Controls

Tests cover secret safety, shared admin/external payload behavior, OpenAPI schema shape, and frontend renderer consumption. The implementation avoids network probes and does not read credential inputs.
