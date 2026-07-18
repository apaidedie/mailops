# Provider Onboarding Guide

This guide is the shortest path for connecting external automation projects to Outlook Email Plus and for adding future temp-mail providers without changing the core API routes.

## Integration model

Outlook Email Plus exposes Outlook, IMAP, pool inventory, and provider-backed temp mailboxes through one provider catalog and one unified mailbox directory. External projects should discover the current instance first, then choose a mailbox source through the provider selection contract.

The stable discovery sequence is:

1. Call `GET /api/v1/external/integration-bundle` with `X-API-Key` and read `data.action_plan` for blocking remediation and next actions.
2. Call `GET /api/v1/external/capabilities` when the caller needs the full capability map.
3. Read top-level `quickstart` or `integration_manifest.quickstart` for the shortest auth, endpoint, provider selector, and request examples.
4. Read `integration_manifest` for full workflow, provider, and deployment hints when the quickstart path is not enough.
5. Call `GET /api/v1/external/providers` when the caller needs the full provider catalog, diagnostics, or per-provider configuration hints.
6. Call `GET /api/v1/external/mailboxes?kind=all&provider=all` when the caller needs the current unified mailbox inventory.
7. Call `GET /api/v1/external/providers/{kind}/{provider}/health` for local readiness, adding `probe_network=true` only when an explicit upstream probe is wanted.

The same provider context is also embedded in mailbox directory responses under `provider_context`, so a client that starts from `/api/v1/external/mailboxes` can still discover selection policy, templates, diagnostics, and documentation links.

For machine clients, `quickstart` is the compact entry point. `/api/v1/external/capabilities`, `/api/v1/external/providers`, and authenticated `/api/providers` expose the same object, and it is also available as `integration_manifest.quickstart`. It is versioned, secret-free, and contains only placeholder auth headers, stable endpoint paths, provider selector fields, minimal request examples, and workflow keys that point back to the full manifest. Use `/api/v1/external/*` only; legacy `/api/external/*` routes were removed.

## Choosing a provider

Provider selection is contract-driven. The source priority is always `env`, `provider_config_file`, `settings`, then `default`.

Use these knobs for deployment-level routing:

- `ACTIVE_MAILBOX_PROVIDERS` restricts which providers are exposed and used.
- `TEMP_MAIL_PROVIDER` chooses the default temp-mail provider for app-side temp-mail creation.
- `EXTERNAL_POOL_DEFAULT_PROVIDER` chooses the default provider for `/api/v1/external/pool/claim-random` when the request body omits `provider`.
- `OUTLOOK_EMAIL_PROVIDER_CONFIG_FILE` points to a JSON or TOML provider selection file. See `.runtime/providers.example.json` and `.runtime/providers.example.toml`.

Use request fields for per-call routing:

- `POST /api/v1/external/pool/claim-random` uses `provider`.
- `POST /api/v1/external/temp-emails/apply` uses `provider_name`.

The allowed values are not hardcoded in this document. Read `selection_policy.scopes.*.allowed_values` or `integration_manifest.selection.recipe_index` from the live instance.

For generated clients and external workers, prefer `readiness_summary.capability_matrix` from `/api/v1/external/providers`, `/api/v1/external/integration-bundle`, or mailbox `provider_context`. It is the provider-neutral selection source: `providers[*]` tells you whether a source is account-backed or temp-mail, which workflows it supports, which selector field/value to send, which read actions and lifecycle actions are available, and whether the provider still needs configuration. `workflows` groups providers by `mailbox_session`, `pool_claim`, `task_temp_mailbox`, `mailbox_directory`, and `provider_health` so callers do not need to hardcode provider names.

## Provider credentials

Discovery payloads may show secret key names such as `DUCKMAIL_BEARER_TOKEN`, `GPTMAIL_API_KEY`, `TEMPMAIL_LOL_API_KEY`, or `EMAILNATOR_API_KEY`. Secret values are never returned.

When generating `.env` files from `deployment_profile.templates.env.content` or `integration_manifest.providers[*].env`, keep every item marked `secret: true` blank and let the operator fill it in privately.

Non-secret defaults can be copied directly. Examples include `MAILTM_API_BASE=https://api.mail.tm` and `DUCKMAIL_API_BASE=https://api.duckmail.sbs`.

## Common workflows

For most external registration workers, read `integration_manifest.workflows[key=start_mailbox_session]` first. The workflow tells the caller how to create a readable mailbox session through `/api/v1/external/mailbox-sessions/start`, receive lifecycle handles, and then use the returned read actions without choosing pool claim versus task temp-mail apply by hand.

For pool-specific registration, read `integration_manifest.workflows[key=claim_pool_mailbox]`. The workflow tells the caller how to claim a mailbox, read messages or verification codes, then complete or release the claim.

For task-scoped temp-mail registration, read `integration_manifest.workflows[key=create_task_temp_mailbox]`. The workflow tells the caller how to create a task mailbox, read from it, then finish the task mailbox.

For mailbox browsing, read `integration_manifest.workflows[key=browse_mailbox_directory]` and the unified mailbox directory contract. The directory returns metadata and action contracts only; message content stays behind the external read endpoints.

## Adding a future temp-mail provider

New temp-mail providers should be added through the plugin contract when possible. The recommended contributor path is the offline provider-dev-kit script, which wraps the existing scaffold and contract validator, adds a local secret scan, and returns either readable text or CI-friendly JSON:

```bash
python scripts/provider_dev_kit.py scaffold <provider_key> --output-dir ./plugins/temp_mail_providers --format json
python scripts/provider_dev_kit.py validate <provider_key> --file ./plugins/temp_mail_providers/<provider_key>.py --format json
```

The generated template already inherits `TempMailProviderBase`, registers with `@register_provider`, exposes provider metadata and `config_schema`, implements every required mailbox/message method, and keeps provider-specific HTTP calls isolated behind request-normalization helpers. The dev-kit `validate` command is offline by default: it imports the local plugin file, runs static contract validation, scans the plugin file for obvious token-like secrets, and does not call provider networks, create mailboxes, delete mailboxes, clear messages, or mutate the database. Use `--probe-options` only when you explicitly want to run the provider `get_options()` shape probe. Use `secret_scan.ok=true` and `contract_validation.status=valid` as the local readiness gate before copying a plugin into a runtime plugin directory.

The legacy low-level commands remain available when you need them directly:

```bash
python web_mailops_app.py scaffold-provider <provider_key>
python web_mailops_app.py validate-provider <provider_key> --file path/to/<provider_key>.py
```

Inheritance is a hard readiness gate, not only a style preference. A provider class that defines matching methods but does not inherit `TempMailProviderBase` is reported as `contract_validation.status=invalid` with `PROVIDER_BASE_CLASS_INVALID`, because the base class owns shared capabilities, health-check shape, and future extension points.

Before copying a provider into production or enabling it in routing, run the local contract checker. The dev-kit command prints `provider-dev-kit` JSON for CI, includes a `secret_scan` object, and exits non-zero for invalid contracts or detected secret values:

```bash
python scripts/provider_dev_kit.py validate <provider_key> --file path/to/<provider_key>.py --format json
```

Use `--probe-options` only when a plugin should also run the local `get_options()` shape probe. The checker never creates, deletes, clears, or mutates mailboxes, and the validation payload is secret-safe. The lower-level `python web_mailops_app.py validate-provider <provider_key> --file <plugin.py> --no-probe-options` command can still be used for parity with the Web API validator.

Every registered temp-mail provider now exposes a secret-free `contract_validation` object through `/api/providers`, `/api/v1/external/providers`, `/api/v1/external/capabilities`, and `integration_manifest.providers[*]`. Plugin authors should treat `contract_validation.status=valid` as the structural readiness gate before enabling a provider in routing. `warning` means the provider can still be discovered but has metadata or local readiness gaps to review. `invalid` means the provider extension contract is incomplete, such as a mismatched provider key, missing required method, invalid config field, or a secret `config_schema` field that defines a default value.

Authenticated operators can inspect a single loaded plugin with `GET /api/plugins/<name>/contract`. This endpoint returns the full validation payload and may run the provider's local `get_options()` shape probe, but it never creates, deletes, clears, or mutates mailboxes and never returns raw provider secret values.

Runtime plugin files are loaded from `<DATABASE_PATH parent>/plugins/temp_mail_providers/` and must be flat `*.py` files. Nested plugin directories are not scanned by the current loader.

After scaffolding a provider, keep the class inheriting `TempMailProviderBase`, replace the generated `_request_json` adapter with the upstream API calls, run `python scripts/provider_dev_kit.py validate <provider_key> --file <plugin.py> --format json`, then run `POST /api/system/reload-plugins` and inspect `GET /api/plugins/<name>/contract` before enabling the provider in routing. Treat `secret_scan.ok=true` plus `contract_validation.status=valid` as the production gate; `warning`, `invalid`, or secret-scan hits should be fixed before adding the provider to `ACTIVE_MAILBOX_PROVIDERS`, `TEMP_MAIL_PROVIDER`, or `EXTERNAL_POOL_DEFAULT_PROVIDER`.

Start with `docs/temp-mail-provider-plugin-guide.md` for the implementation contract. Use `docs/temp-mail-provider-plugin-prompt.md` when handing one concrete provider API document to an AI agent.

After a provider is installed, it should appear through `/api/providers`, `/api/v1/external/providers`, `/api/v1/external/capabilities`, and mailbox `provider_context` without adding provider-specific routes or frontend tables.

## Verification checklist

Before treating a provider or external integration as ready, verify these conditions:

- `python scripts/project_readiness_check.py` passes before release or deployment handoff, and `python scripts/project_readiness_check.py --format json` is usable as a local CI gate.
- `python scripts/provider_dev_kit.py scaffold <provider_key> --format json` generates a plugin skeleton with placeholder configuration only.
- `python scripts/provider_dev_kit.py validate <provider_key> --file <plugin.py> --format json` exits `0`, reports `secret_scan.ok=true`, and reports `contract_validation.status=valid` before the provider is copied into production.
- `/api/v1/external/capabilities` returns `integration_manifest`, top-level `quickstart`, `selection_policy`, `provider_integration_guide`, and `documentation`.
- Top-level `quickstart` equals `integration_manifest.quickstart` on capabilities, external providers, and authenticated providers payloads.
- `integration_manifest.documentation.entries.provider_onboarding.path` points to this file.
- `integration_manifest.selection.source_priority` is `env`, `provider_config_file`, `settings`, `default`.
- Secret fields in manifest provider env hints use empty `value` strings.
- `integration_manifest.providers[*].contract_validation` and provider catalog rows report `status=valid` for production providers.
- Custom provider classes inherit `TempMailProviderBase`; non-base classes fail validation with `PROVIDER_BASE_CLASS_INVALID` even if every required method is present.
- `python web_mailops_app.py validate-provider <provider_key> --file <plugin.py>` still exits `0` and reports `contract_validation.status=valid` for low-level validator parity.
- `GET /api/plugins/<name>/contract` returns no API key values, bearer tokens, passwords, JWTs, task tokens, consumer keys, or secret config defaults.
- `GET /api/v1/external/providers/{kind}/{provider}/health` reports `ready` or the expected `needs_config` reason.
- Provider-specific pool claims use `provider`; task temp-mail creation uses `provider_name`.
- `GET /api/v1/external/openapi.json` exposes the same discovery and provider selection schemas for generated clients.
- `GET /api/v1/external/integration-bundle` returns `data.action_plan`; blocking items are resolved before mailbox sessions are started.
- `scripts/external_api_smoke.py --base-url <url> --api-key <key>` passes before mutating mailbox state.
