# Provider diagnostics and routing hardening

## Goal

Strengthen the unified mailbox platform's provider-routing contract so operators and external integrators can decide which provider to use without reverse-engineering several discovery payloads. The next increment adds a secret-free provider routing matrix to the shared readiness summary that is already consumed by `/api/providers`, `/api/external/providers`, `/api/mailboxes`, external capabilities, OpenAPI, and the unified mailbox UI.

## Confirmed Facts

- Provider selection is centralized in `mailops.services.provider_catalog.get_mailbox_provider_selection_policy()` with source priority `env`, `provider_config_file`, `settings`, then `default`.
- Provider discovery payloads already expose `provider_integration_guide`, `integration_manifest`, `quickstart`, `selection_policy`, `documentation`, and compact `readiness_summary` projections.
- The unified mailbox directory is the main aggregation surface for Outlook/Graph, IMAP, temp-mail providers, and external API entry points.
- Current readiness provider rows expose readiness, inventory counts, endpoints, and capabilities, but do not explicitly state which selection scopes each provider can be used for.

## Requirements

1. Add a `routing_matrix` object to mailbox provider readiness summaries.
2. The matrix must be generated in `provider_catalog`, not controllers or frontend code.
3. The matrix must cover at least these scopes:
   - `temp_runtime_default`
   - `task_temp_apply`
   - `pool_claim_default`
   - `explicit_pool_claim`
4. Each scope entry must expose the request/config field, endpoint when applicable, allowed values, provider rows, and aggregate counts.
5. Provider rows must be secret-free and include provider key, label, kind, active/configured state, usable boolean, status/reason, aliases, and endpoint hints.
6. The matrix must preserve alias-aware compatibility for GPTMail/legacy temp-mail aliases and IMAP pool aliases by reusing existing selection policy and guide data.
7. OpenAPI schemas must document the new readiness matrix enough for generated clients to treat it as a stable contract.
8. Frontend rendering may consume the matrix to improve the unified mailbox source-policy status band, but must stay provider-agnostic and must not branch on built-in provider names.

## Acceptance Criteria

- [ ] Backend tests prove `/api/providers` readiness summary includes `routing_matrix` with the required scopes and scope-level provider rows.
- [ ] Unified mailbox directory tests prove `provider_context.readiness_summary.routing_matrix` is present and secret-free.
- [ ] OpenAPI tests prove `MailboxProviderReadinessSummary` requires and documents `routing_matrix`.
- [ ] Frontend contract tests prove the unified mailbox UI consumes `readinessSummary.routing_matrix` without reading Settings credential inputs or branching on provider names.
- [ ] Existing provider discovery, unified mailbox, and browser-extension scoped tests remain green.

## Out of Scope

- Adding a brand-new upstream provider.
- Running destructive upstream health probes by default.
- Replacing the provider plugin system.
- Reworking the whole app visual design in this single increment.
