# Provider Plugin Scaffold CLI

## Goal

Make future temp-mail provider additions faster by adding a local CLI command that creates a new provider plugin file from the tested example template, without changing runtime plugin loading, provider discovery, external API routes, or database schema.

## Background

- The project already has a tested template at `examples/temp_mail_provider_plugin_template.py`.
- Runtime plugin files are loaded from `<DATABASE_PATH parent>/plugins/temp_mail_providers/*.py`.
- `outlook_web.services.temp_mail_plugin_cli` already owns plugin install, uninstall, and list commands.
- Provider extension should stay contract-driven and secret-free; generated files must not contain real credentials or secret defaults.

## Requirements

- Add a CLI command that scaffolds a new temp-mail provider plugin file from the tested template.
- The command must accept a provider key and optional output directory.
- Provider keys must be stable ASCII identifiers compatible with the provider contract and plugin loader filename rules.
- The generated file must replace the template provider key/class/label with values derived from the requested provider key.
- The command must refuse to overwrite an existing plugin unless an explicit force flag is passed.
- The command must print the generated path and a next-step reminder to reload plugins and inspect contract validation.
- The scaffold path must be implemented in the plugin CLI/manager layer only; it must not add provider-specific runtime routes, database tables, or external API branches.
- Generated files must not include real API keys, bearer tokens, passwords, or secret config defaults.
- Update provider onboarding documentation to mention the scaffold command.

## Acceptance Criteria

- [x] `python web_outlook_app.py scaffold-provider <provider_key>` style CLI routing exists through `temp_mail_plugin_cli.main()`.
- [x] Unit tests prove the command writes a provider plugin file derived from `examples/temp_mail_provider_plugin_template.py`.
- [x] Unit tests prove invalid provider keys are rejected and existing files are not overwritten without `--force`.
- [x] Unit tests prove `--force` can replace an existing generated file.
- [x] Unit tests prove the generated plugin imports, registers under the requested key, and passes `validate_temp_mail_provider_class(..., probe_options=True)`.
- [x] Provider onboarding docs mention the scaffold command next to the template guidance.
- [x] No provider loading semantics, external API routes, or database schema are changed.
- [x] Focused plugin CLI/template tests pass.

## Out Of Scope

- UI wizard for provider scaffolding.
- Installing third-party dependencies.
- Implementing a real provider for another upstream API.
- Changing plugin registry, reload, or discovery semantics.
