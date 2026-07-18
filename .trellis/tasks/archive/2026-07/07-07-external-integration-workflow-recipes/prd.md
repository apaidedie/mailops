# External integration workflow recipes

## Goal

Make the existing `integration_manifest` more useful for external projects by adding secret-safe, machine-readable workflow recipes for the registration automation path: discover the API contract, inspect available mailboxes/providers, claim or create a mailbox, read messages or verification codes, then release, complete, or finish the mailbox lifecycle.

## Background

The current manifest already exposes API key metadata, discovery endpoints, provider selection fields, deployment hints, and per-provider env/settings keys. External clients can generate starter config from it, but they still have to infer the end-to-end operation order from several separate payload sections and README prose.

The provider selection contract requires `integration_manifest` to be generated in `mailops.services.provider_catalog` from the same guide, selection policy, deployment profile, diagnostics, and endpoint map as the owning response. It must remain additive, provider-agnostic, and secret-safe.

## Requirements

- Add a top-level `workflows` section to `integration_manifest` for `/api/providers`, `/api/external/providers`, `/api/external/capabilities`, and OpenAPI `x-capabilities.integration_manifest`.
- Represent workflows as stable machine-readable objects with keys, labels, descriptions, and ordered steps. Steps must include method, endpoint, auth requirement, request field hints, response field hints, and next-action guidance where useful.
- Cover the main external automation paths: discovery, mailbox directory browse, pool mailbox claim/read/complete-or-release, and task temp-mail create/read/finish.
- Derive provider override request fields and allowed values from `selection_policy.scopes.explicit_pool_claim` and `selection_policy.scopes.task_temp_apply` instead of maintaining a second enum.
- Derive endpoint paths from the external endpoint map and existing read contract helpers instead of duplicating literals where the codebase already owns the contract.
- Keep the manifest provider-agnostic. Do not branch workflow construction on provider names such as DuckMail, Mail.tm, GPTMail, TempMail.lol, or Emailnator.
- Keep workflow data secret-safe. Secret key names may appear only where existing manifest provider hints already allow key names, but workflow recipes must not expose API key values, provider tokens, bearer tokens, passwords, JWTs, refresh tokens, task tokens, or consumer keys.
- Update OpenAPI component schemas so generated clients can type `integration_manifest.workflows` instead of treating it as an unstructured extension.
- Update tests for runtime payloads, OpenAPI schemas, and secret-safety.

## Out of Scope

- No endpoint behavior changes.
- No new provider integration.
- No frontend UI changes unless a test proves the current starter kit breaks on the additive field.
- No real provider credential or DuckMail token value may be written to code, docs, tests, logs, or task artifacts.

## Acceptance Criteria

- `/api/external/capabilities` returns `integration_manifest.workflows` with stable recipe keys for discovery, mailbox directory browsing, pool claim lifecycle, and task temp-mail lifecycle.
- `/api/external/providers` and authenticated `/api/providers` expose the same workflow recipe contract through the same manifest builder.
- Workflow recipe request fields for pool claim and task temp-mail apply match the current selection policy request fields and allowed values.
- Read steps reference the existing external message and verification-code read contracts without leaking mailbox secrets.
- `/api/external/openapi.json` includes typed `IntegrationManifestWorkflow` and `IntegrationManifestWorkflowStep` component schemas, and `x-capabilities.integration_manifest.workflows` mirrors runtime output.
- Tests prove workflow payloads do not contain real secret values or hardcoded provider-specific branches.
- Existing provider selection, provider catalog, external temp-mail, and unified mailbox tests still pass.
