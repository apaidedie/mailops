# Unified mailbox command center

## Goal

Make the dashboard first viewport answer whether the unified mailbox service is usable now. It should summarize mailbox inventory, provider readiness, external API integration readiness, and the next operational actions without forcing the user to jump between Unified Mailbox, Provider Settings, and External API tabs.

## Background

- The project already has a unified mailbox directory page backed by `/api/mailboxes`.
- The unified mailbox payload already exposes `provider_context.readiness_summary` with provider totals, routing matrix, and secret-free diagnostics.
- The External API area already exposes discovery, OpenAPI, integration bundle, and operational readiness details.
- The current dashboard summary shows account, pool, refresh, and daily KPI cards, but it does not provide a single command-center summary for the full mailbox aggregation product.

## Requirements

- Add a secret-free command-center summary to `/api/overview/summary`.
- The backend summary must be local/read-only and must not probe provider networks.
- The summary must include mailbox source mix, provider readiness counts, external API readiness status, and a bounded action plan.
- The dashboard summary tab must render this command center above the existing KPI cards.
- The UI must stay operational and data-dense, using existing Flask templates, static JS, CSS variables, and dashboard component patterns.
- The UI must not add a new frontend framework, decorative gradients, structural emoji, or cards nested inside cards.
- All user-visible labels must be translatable through the existing i18n mechanism.
- Secrets, API keys, bearer tokens, task tokens, and masked key internals must not be exposed in API responses, tests, docs, logs, or rendered UI.

## Acceptance Criteria

- [ ] `/api/overview/summary` returns `command_center` with stable fields for `overall_status`, `mailbox_inventory`, `provider_readiness`, `external_api`, and `actions`.
- [ ] `command_center` contains only counts, statuses, endpoint paths, docs paths, and action metadata; it contains no secret values or secret field names beyond non-sensitive environment variable names already documented for provider setup.
- [ ] The summary tab renders a top-level `ov-command-center` section before the KPI row.
- [ ] The rendered command center shows mailbox inventory, provider readiness, External API readiness, and next actions with responsive, stable dimensions.
- [ ] Focused backend and frontend contract tests cover the new schema, rendering hooks, i18n labels, CSS classes, and secret-safety boundaries.
- [ ] Desktop and mobile rendered checks show no blank dashboard, overflow, or incoherent overlap.

## Out Of Scope

- Adding new mailbox providers.
- Changing provider selection semantics.
- Running upstream provider health probes from the dashboard.
- Replacing the existing dashboard tab architecture.
- Introducing React, Tailwind, shadcn/ui, or another component library.
