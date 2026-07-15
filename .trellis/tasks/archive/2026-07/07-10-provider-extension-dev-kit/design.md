# Provider extension developer kit design

## Boundaries

The developer kit is a thin contributor workflow layer over the existing provider plugin system. It must reuse:

- `scaffold_provider_plugin(...)` for file generation.
- `validate_temp_mail_provider_class(...)` and the existing local plugin import path for structural contract validation.
- The project readiness secret-pattern vocabulary so secret checks stay consistent with release gates.

It must not introduce provider-specific branches for Mail.tm, DuckMail, TempMail.lol, Emailnator, or future providers. Provider-specific behavior remains in provider plugin classes.

## Command Shape

Add `scripts/provider_dev_kit.py` with two subcommands:

- `scaffold <provider_key>` generates a provider file and returns generated path, class name, validation command, and next steps.
- `validate <provider_key> --file <plugin.py>` imports and validates a local provider file, runs a local secret scan, and returns a combined report.

Both subcommands support `--format text|json`. Validation defaults to static/offline checks. `--probe-options` explicitly opts into the provider `get_options()` shape probe.

## Report Contract

The JSON report should be stable enough for CI and examples:

- `success`: boolean gate result.
- `command`: `scaffold` or `validate`.
- `provider`: provider key.
- `file_path`: generated or validated path.
- `contract_validation`: full validation payload for validate, or optional generated-file validation if run by scaffold.
- `secret_scan`: `{ok, hits}` with hits shaped as `{file, line, pattern}` and no matched values.
- `next_steps`: safe local commands and documentation hints.

Text output is operator-friendly but secondary. Tests should assert JSON for stability.

## Data Flow

Scaffold flow:

1. Normalize provider key through `scaffold_provider_plugin`.
2. Write the plugin into the requested output directory.
3. Return safe next-step commands, including the dev-kit validation command and the existing `web_outlook_app.py validate-provider` command.

Validation flow:

1. Import the plugin file using the same loader semantics as existing CLI validation.
2. Resolve the provider class from the temp-mail registry.
3. Run `validate_temp_mail_provider_class(provider_key, provider_cls, probe_options=<explicit flag>)`.
4. Scan only the target plugin file for obvious secret values.
5. Return success only if contract status is `valid` and the secret scan is clean.

## Compatibility

- Existing `web_outlook_app.py scaffold-provider` and `validate-provider` commands remain compatible.
- Existing provider template, loader, and web API payloads remain unchanged unless a small reusable helper is needed for the script.
- No database migration is required.

## Operational Safety

- Default validation is offline and does not call provider networks.
- Validation does not create, delete, clear, or mutate mailboxes.
- Secret hits report pattern metadata only.
- Generated files use placeholders only.

## Rollback

The change is additive. Rollback is limited to removing the script, tests, docs additions, readiness-check additions, and any small helper refactor made for validation reuse.
