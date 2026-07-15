# Dedupe bridge aliases in readiness and protect catalog radios

## Goal

1. Collapse `custom_domain_temp_mail` / `legacy_bridge` (and other built-in aliases) into one readiness/capability/routing row so operators do not see duplicate Compatible Bridge entries.
2. Stop PluginManager radio/select injection from overwriting catalog-rendered labels/descriptions when the provider already exists.

## Problem / evidence

- Backend catalog still emits both `legacy_bridge` and `custom_domain_temp_mail` as separate temp rows with the same human label.
- Settings/create selectors already canonicalize via `normalizeTempMailSettingsProviderName`; readiness/capability lists do not.
- `_refreshProviderRadios` / `_refreshProviderSelect` overwrite existing catalog option text with plugin display_name / emoji.

## Requirements

- Frontend dedupe of temp provider rows by canonical provider key; merge mailbox counts when collapsing.
- Plugin inject only tags existing catalog radios/options; do not rewrite name/desc/text when already present.
- Still inject missing installed plugins not in catalog (warmup fallback).
- Contract tests cover both behaviors.

## Acceptance Criteria

- [x] Readiness/capability/routing paths use canonical provider keys and de-dupe.
- [x] Plugin inject preserves catalog radio/option labels.
- [x] Focused tests + `git diff --check` pass.

## Out Of Scope

- Removing backend dual catalog entries (larger compatibility change).
- UI visual redesign / screenshots.
