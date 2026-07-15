# Unified Provider Capability Matrix

## Goal

Expose a machine-readable provider capability matrix across Outlook/Graph, IMAP, mailbox-pool, built-in temp-mail, and plugin temp-mail sources so external services can choose mailbox sources without hardcoding provider-specific behavior.

## Background

- The provider catalog already owns provider diagnostics, provider integration guide, routing matrix, and readiness summary.
- External providers API, capabilities, mailbox directory context, integration bundle, and OpenAPI already reuse `get_mailbox_provider_readiness_summary()`.
- Current readiness rows expose status and a few capabilities, but there is no compact matrix that groups provider support by workflow or operation for external client selection.

## Requirements

- Add a versioned `capability_matrix` to `MailboxProviderReadinessSummary` from the provider catalog layer.
- The matrix must be secret-free and derived from existing provider catalog / integration guide / routing matrix data.
- The matrix must include per-provider capability rows for account and temp providers, with stable fields for source kind, read capability, dynamic creation, pool inventory requirement, session support, pool-claim support, task-temp support, directory visibility, read actions, lifecycle actions, configuration status, config source, aliases, and endpoint hints.
- The matrix must include workflow groups for at least `mailbox_session`, `pool_claim`, `task_temp_mailbox`, `mailbox_directory`, and `provider_health`, each with provider counts and provider keys.
- The matrix must include totals for account providers, temp providers, dynamic-create providers, pool-inventory providers, task-temp-capable providers, pool-claim-capable providers, session-capable providers, and providers needing config.
- OpenAPI must document the matrix in `MailboxProviderReadinessSummary` with typed schemas.
- External API tests must verify the matrix exists on provider discovery/readiness surfaces and remains secret-free.

## Acceptance Criteria

- [x] `/api/v1/external/providers` and legacy provider discovery expose `data.readiness_summary.capability_matrix`.
- [x] The matrix contains rows for account and temp providers and includes known providers such as `mail_tm`, `duckmail`, and an account provider.
- [x] Matrix workflow groups expose counts and provider keys for mailbox sessions, pool claim, task temp-mail, mailbox directory, and provider health.
- [x] Matrix rows expose selection fields and endpoint hints without provider secret values.
- [x] OpenAPI contains `MailboxProviderCapabilityMatrix`, row, workflow, and totals schemas and references them from `MailboxProviderReadinessSummary`.
- [x] Docs mention the capability matrix as the provider-neutral selection source for external workers.
- [x] Targeted tests and project readiness checks pass.

## Out Of Scope

- Adding a new external endpoint.
- Changing provider selection behavior or provider defaults.
- Running upstream network probes.
- Adding frontend UI for the matrix in this task.
