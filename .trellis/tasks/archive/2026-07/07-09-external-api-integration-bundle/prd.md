# External API integration bundle

## Goal

Make Outlook Email Plus easier to embed into external registration workers and batch services by adding a read-only integration-bundle output to the existing Python starter client.

The bundle should turn live discovery data into a compact machine-readable package that downstream services can inspect, commit into their own deployment planning, or feed into CI without hand-copying endpoints and provider selection templates from several documents.

## Confirmed Facts

- `examples/external_api_python_client.py` already performs read-only discovery through capabilities, providers, and OpenAPI, and mutating mailbox session demos through `verification-code`.
- `capabilities.data` already exposes `endpoints`, `documentation`, `integration_manifest`, `deployment_profile`, `selection_policy`, and mailbox session hints.
- `deployment_profile.templates` already contains env and JSON/TOML provider-config templates.
- `docs/external-integration-quickstart.md` explains smoke checks and starter clients, but there is no one-command bundle summarizing live endpoints, provider values, templates, workflows, and docs links for another service.
- The bundle must not fetch messages, start sessions, claim pool mailboxes, create task temp-mailboxes, probe provider networks, or write provider secrets.

## Requirements

- Add a read-only `integration-bundle` command to `examples/external_api_python_client.py`.
- The command must call the same discovery path as `discover`; it must not call mutating session, pool, temp-mail, or message endpoints.
- The JSON bundle must include:
  - `base_url` and discovered `endpoints`;
  - `auth` summary with header name and placeholder only;
  - `documentation` entries from capabilities;
  - provider `source_priority` and `provider_values` from deployment or selection policy;
  - `templates` for env, provider config JSON, and provider config TOML when available;
  - `workflows` as compact workflow keys and labels from `integration_manifest`;
  - `readiness` summary derived from providers/readiness data when available;
  - `openapi` summary with version and path count.
- The command must support `--output path`. Without `--output`, print the bundle JSON to stdout. With `--output`, write the JSON file and print only the output path.
- The generated bundle must never include the caller's API key or obvious provider secret values.
- Update `docs/external-integration-quickstart.md` with the new command.

## Acceptance Criteria

- [x] `integration-bundle` produces parseable JSON on stdout by default.
- [x] `integration-bundle --output <path>` writes the same parseable JSON to disk and prints the path.
- [x] The bundle includes endpoints, auth placeholder, documentation entries, provider values, templates, workflows, readiness, and OpenAPI summary from fake discovery payloads.
- [x] Tests prove the command is read-only by asserting only GET discovery calls occur.
- [x] Tests prove the bundle does not include the API key or obvious provider secret values.
- [x] Quickstart docs show how an external service can generate the bundle.
- [x] Existing Python starter discovery and verification tests still pass.
- [x] `python -m py_compile examples/external_api_python_client.py` passes.
- [x] `git diff --check` reports no whitespace errors.

## Out of Scope

- No backend route changes.
- No generated client SDK files beyond the JSON bundle.
- No provider-specific network probes.
- No lifecycle mutation or mailbox reads.
