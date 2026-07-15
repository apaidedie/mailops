# Provider extension developer kit

## Goal

Make future temp-mail provider extensions faster and safer to build by packaging the existing provider scaffold, contract validator, secret-safety checks, and contributor instructions into an offline developer kit.

The kit should help a contributor add a new provider such as a Mail.tm-compatible deployment, TempMail.lol, or Emailnator without changing core API routes or leaking credentials into examples, docs, tests, or command output.

## Confirmed Facts

- The project already has a provider plugin contract based on `TempMailProviderBase`, `@register_provider`, provider metadata, `config_schema`, and required mailbox/message methods.
- `python web_outlook_app.py scaffold-provider <provider_key>` already generates a provider plugin from `examples/temp_mail_provider_plugin_template.py`.
- `python web_outlook_app.py validate-provider <provider_key> --file <plugin.py>` already imports a local plugin and prints structured contract validation JSON.
- Provider discovery payloads already include secret-free `contract_validation` metadata.
- `scripts/project_readiness_check.py` already guards integration docs, examples, config templates, and obvious checked-in secrets.
- Runtime plugin validation must remain offline by default and must not create, delete, clear, or mutate mailboxes.

## Requirements

- Add a contributor-facing provider developer kit entry point that wraps existing scaffold and validation helpers instead of duplicating provider internals.
- The default validation flow must be offline: it may import a local provider file and run static contract validation, but it must not opt into provider network probes unless explicitly requested.
- The developer kit must produce machine-readable JSON and concise text output with provider key, generated file path or validated file path, contract status, issue codes, secret-scan status, and next-step commands.
- The developer kit must scan target plugin files for obvious secret values and report only file, line, and pattern names, never the secret text.
- Documentation must describe the developer kit as the recommended path for new providers and must keep provider-specific credentials as placeholders only.
- The repository readiness check must fail if the developer kit assets or documentation contract drift.
- Tests must cover scaffold output, offline validation, JSON output, secret detection, and readiness-check coverage.

## Acceptance Criteria

- [ ] A command such as `python scripts/provider_dev_kit.py scaffold <provider_key> --output-dir <dir> --format json` generates a plugin file through the existing scaffold helper and returns parseable JSON.
- [ ] A command such as `python scripts/provider_dev_kit.py validate <provider_key> --file <plugin.py> --format json` validates a local plugin without probing network-capable provider options by default.
- [ ] The validation report exits `0` only when the contract is valid and the secret scan has no hits; it exits non-zero for invalid contracts or detected secrets.
- [ ] Secret-scan output contains pattern metadata but not matched secret values.
- [ ] `docs/provider-onboarding.md` documents the dev-kit flow, offline default, optional probe flag, JSON mode, and production readiness gate.
- [ ] `scripts/project_readiness_check.py` includes the dev-kit script and docs contract in its local gate.
- [ ] Focused provider dev-kit tests, existing provider CLI/contract tests, readiness check, and whitespace check pass.

## Out of Scope

- Adding new live provider integrations in this task.
- Changing the external API route surface.
- Changing production provider routing, stored credentials, or database schema.
- Calling upstream provider networks during default validation.
