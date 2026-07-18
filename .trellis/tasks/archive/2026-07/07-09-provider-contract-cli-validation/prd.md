# Provider contract CLI validation

## Goal

Add a local/CI-friendly Provider contract validation command so plugin authors can validate a new temp-mail provider before enabling it in the Web UI or routing policy.

This improves the project's extensibility goal: future mailbox kinds and provider-backed temp-mail services should be easy to add without editing external API routes or guessing whether the plugin contract is complete.

## Confirmed Facts

- `mailops.services.temp_mail_provider_contract.validate_temp_mail_provider_class()` is already the authoritative validator for temp-mail provider classes.
- `GET /api/plugins/<name>/contract` exposes the same validation for loaded plugins, but it requires a running authenticated Web app.
- `python web_outlook_app.py scaffold-provider <provider_key>` already generates a valid plugin file from `examples/temp_mail_provider_plugin_template.py`.
- `mailops.services.temp_mail_plugin_cli` currently supports `install-provider`, `uninstall-provider`, `scaffold-provider`, and `list-providers`, but has no direct validation command.
- `web_outlook_app.py` only forwards those four CLI commands to `temp_mail_plugin_cli.main()`.

## Requirements

- Add a `validate-provider` CLI command reachable through `python web_outlook_app.py validate-provider <provider_key>`.
- Allow validating an already registered provider from the current registry.
- Allow validating an arbitrary plugin file with `--file <path>` so CI can validate a generated or downloaded plugin before copying it into the runtime plugin directory.
- Use the existing `validate_temp_mail_provider_class()` result without reimplementing contract checks in the CLI.
- Support `--no-probe-options` to skip the `get_options()` shape probe when a plugin should be statically inspected only.
- Print machine-readable JSON by default so CI and external automation can parse validation status, issue codes, and summaries.
- Exit `0` only for `status=valid`; exit `2` for `warning` or `invalid`; exit `1` for load/argument/runtime errors.
- Keep output secret-safe: do not print raw provider config values, bearer tokens, API keys, task tokens, JWTs, passwords, or consumer keys.
- Update provider onboarding docs to recommend the CLI validation command before reload/enabling.

## Acceptance Criteria

- [x] `python web_outlook_app.py validate-provider template_temp_mail --file examples/temp_mail_provider_plugin_template.py` exits `0` and prints JSON with `contract_validation.status=valid`.
- [x] A provider with a secret config default exits non-zero and does not print the secret value.
- [x] An unknown provider without `--file` exits `1` with a structured error message.
- [x] Tests cover the CLI helper and `web_outlook_app.py` command forwarding.
- [x] Provider onboarding docs include the local validation step.
- [x] Existing temp-mail plugin/contract tests continue to pass.
- [x] `git diff --check` reports no whitespace errors.

## Out of Scope

- No changes to provider validation semantics.
- No network probes, mailbox creation, message reads, or mailbox mutation.
- No new Web UI panel or external API endpoint.
