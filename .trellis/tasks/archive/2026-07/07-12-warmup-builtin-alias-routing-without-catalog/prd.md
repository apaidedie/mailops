# Warmup built-in alias routing without catalog

## Goal

During catalog warmup, canonicalize known built-in temp-provider aliases (e.g. `gptmail`, `custom_domain_temp_mail`) to schema-panel providers so they are not misrouted to PluginManager.

## Problem / evidence

- `normalizeTempMailSettingsProviderName` only resolves aliases from catalog cache.
- Before `/api/providers` loads, saved values like `gptmail` / `custom_domain_temp_mail` stay uncanonicalized.
- `providerUsesTempSettingsSchemaPanel` then treats them as unknown + PluginManager → empty plugin panel instead of bridge schema.

## Requirements

- Static alias map for legacy bridge historical names when catalog is empty/missing match.
- Built-in fallback list remains after canonicalization.
- Contract tests assert static alias markers and warmup routing.

## Acceptance Criteria

- [x] Known aliases normalize without catalog.
- [x] Warmup routing keeps those providers on schema path.
- [x] Focused tests + `git diff --check` pass.

## Out Of Scope

- Changing backend alias contracts.
