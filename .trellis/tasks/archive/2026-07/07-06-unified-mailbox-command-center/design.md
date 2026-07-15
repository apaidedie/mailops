# Unified mailbox command center design

## UI Brief

Audience: operators and developers using Outlook Email Plus as a mailbox aggregation service for registration, verification, and external automation.

Primary workflow: enter mailbox unified mode, understand active inventory and routing policy, then filter/open/copy mailboxes or inspect provider readiness.

Product archetype: operational SaaS command center. The visual language should be dense, calm, and precise rather than marketing-heavy.

Constraints: existing Flask/Jinja, vanilla JS, CSS tokens, bilingual i18n, no new packages, no provider-specific frontend rules, and no backend contract changes.

Source of truth: existing `/api/mailboxes` payload and current unified mailbox/provider frontend code.

States: loading, error, no provider context, ready, all providers enabled, allowlist enabled, no mailbox results, mobile stacked layout.

Acceptance: contract tests plus rendered desktop/mobile checks when feasible.

## Data Flow

`loadUnifiedMailboxes()` already receives `summary`, `facets`, `filters`, `provider_context`, and `contract`. A new `renderUnifiedCommandCenter(data, state)` helper will derive display rows from those same fields and write into `#unifiedMailboxCommandCenter`.

The helper will use existing utilities where possible: `formatUnifiedMailboxCount()`, `normalizeUnifiedFacetCount()`, `translateUnifiedText()`, `getUnifiedProviderContextText()`, and provider-context parsing helpers. It will not introduce a local provider registry.

## Display Model

The command center has three parts:

- A compact title and route summary describing the unified mailbox fabric.
- Four metrics: total inventory, account/temp mix, provider readiness, and active routing.
- Workflow chips for account mailboxes, temporary mailboxes, provider routing, and external API access.

The external API chip uses `provider_context.provider_integration_guide.endpoints.mailboxes` first, with `provider_context.discovery.mailboxes_endpoint` as a fallback if present. Source priority comes from `provider_context.selection_policy.source_priority`.

## Compatibility

The new mount sits above the existing toolbar and does not replace existing filters, result bar, provider context, mailbox card rendering, or open/copy flows. The command center is read-only. Existing state refresh and language-change reload behavior remain intact.

## Rollback

Rollback is limited to removing the template mount, JS render helper and calls, CSS classes, i18n entries, tests, and task artifacts.
