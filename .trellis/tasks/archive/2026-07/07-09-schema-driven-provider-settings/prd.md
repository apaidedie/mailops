# Schema Driven Provider Settings

## Goal

Make Settings -> Temp Mail provider configuration catalog/schema driven so operators can configure built-in temp-mail providers with the same mental model used by plugin providers. This supports the broader product goal of a unified, extensible mailbox aggregation service by reducing provider-specific UI branches and making future mailbox provider additions cheaper and safer.

## Background

- The temp-mail provider selector is already rendered from the backend provider catalog.
- Built-in temp-mail providers expose configuration metadata through `outlook_web/services/provider_catalog.py`, including settings keys, required settings, secret settings, and defaults.
- Plugin providers already expose a `config_schema` path consumed by `static/js/features/plugins.js`.
- Settings -> Temp Mail still contains built-in provider-specific configuration panels and JavaScript routing/collection logic for providers such as legacy bridge, Cloudflare Worker temp mail, DuckMail, Emailnator, Mail.tm, and TempMail.lol.

## Requirements

1. Add a provider-agnostic configuration surface for built-in temp-mail providers whose required settings can be projected from catalog metadata.
2. Reuse catalog/provider metadata already available to Settings instead of adding a second hardcoded provider registry in the frontend.
3. Preserve existing saved settings semantics for `active_mailbox_providers`, provider defaults, base URLs, and provider secret settings.
4. Keep secret handling safe: never render saved bearer tokens, API keys, passwords, refresh tokens, JWTs, task tokens, consumer keys, or provider secret values into the DOM, copied text, logs, docs, tests, or command output.
5. Let secret fields show key names, required state, masked/preserved hints, and empty password inputs without pre-filling secret values.
6. Keep special provider workflows working where they exist today, including Cloudflare Worker domain sync and plugin-provider schema rendering.
7. Improve the Settings Temp Mail UI structure enough that long provider labels, endpoint paths, key names, and helper text wrap cleanly on desktop and mobile.
8. Do not add a frontend framework, component library, build step, or new UI dependency for this slice.
9. Keep changes compatible with provider discovery contracts, external API discovery, and readiness/preflight payloads.

## Acceptance Criteria

- [ ] Settings -> Temp Mail includes a generic built-in provider configuration panel fed by provider catalog/settings metadata.
- [ ] Mail.tm-compatible providers (`mail_tm`, `duckmail`, and `tempmail_lol`) can be represented without adding separate provider-specific template panels.
- [ ] Emailnator settings can be represented through the generic surface or through a clearly isolated compatibility path without increasing provider-specific branch growth.
- [ ] Existing Cloudflare Worker and plugin-provider special flows still render and save correctly.
- [ ] Saving Settings preserves existing values for untouched secret fields and does not serialize masked placeholders as real secrets.
- [ ] Frontend contract tests cover the generic panel mount, provider routing behavior, schema/metadata rendering, secret-safety constraints, and responsive CSS hooks.
- [ ] Backend/provider contract tests that cover provider catalog configuration remain green.
- [ ] `node --check static/js/main.js` passes.
- [ ] Targeted pytest suites for Settings provider UI and temp-mail provider contracts pass.
- [ ] A rendered browser check covers Settings -> Temp Mail on desktop and mobile with no page-level or panel-level horizontal overflow.

## Out Of Scope

- Replacing the complete Settings page design system in this slice.
- Changing provider runtime implementation, upstream API behavior, or external mailbox session lifecycle semantics.
- Removing legacy bridge or Cloudflare Worker support.
- Pushing commits to a remote repository.
