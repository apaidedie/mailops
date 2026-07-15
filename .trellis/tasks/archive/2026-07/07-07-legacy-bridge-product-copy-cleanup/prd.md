# Legacy bridge product copy cleanup

## Goal

Remove GPTMail as a formal product-facing provider label while preserving the existing compatibility aliases, environment variables, settings migration path, and runtime behavior. The unified platform should present the legacy/self-hosted compatible temp-mail path as a generic compatible bridge, not as a branded GPTMail product.

## Background

The parent platform task requires de-emphasizing legacy GPTMail branding from product-facing surfaces while keeping compatibility aliases and migration behavior. Current evidence shows that `outlook_web/services/provider_catalog.py` maps `legacy_bridge`, `custom_domain_temp_mail`, and compatibility aliases to the label `GPTMail`, README files document `GPTMAIL_*` as first-class setup knobs, `.env.example` names the compatible bridge as old GPTMail, and settings tests still assert `temp_mail_provider_label == "GPTMail"`.

Compatibility must remain intact because legacy deployments may still set `GPTMAIL_BASE_URL`, `GPTMAIL_API_KEY`, `TEMP_MAIL_PROVIDER=gptmail`, `legacy_gptmail`, or `temp_mail`, and provider discovery must keep documenting those aliases for external callers.

## Requirements

- Change formal provider labels for `legacy_bridge`, `custom_domain_temp_mail`, `legacy_gptmail`, `gptmail`, and `temp_mail` to generic compatible-bridge wording in backend discovery and settings-facing data.
- Preserve canonical provider keys, alias maps, environment variable names, settings keys, request fields, config-file fields, and secret-safe discovery behavior.
- Update product-facing README and `.env.example` copy so `GPTMAIL_*` is described as a legacy-compatible bridge configuration rather than a current branded provider.
- Keep explicit compatibility notes where useful so existing operators understand that old `GPTMAIL_*` env names still work.
- Update focused tests that currently expect GPTMail as a formal label and add coverage proving aliases remain present.

## Acceptance Criteria

- [ ] `/api/settings` exposes a generic compatible-bridge label for saved `custom_domain_temp_mail` instead of `GPTMail`.
- [ ] Provider discovery labels for the legacy bridge family no longer present `GPTMail` as the formal provider label, while alias maps still include `gptmail`, `legacy_gptmail`, and `temp_mail`.
- [ ] README, README.en, and `.env.example` explain `GPTMAIL_BASE_URL` / `GPTMAIL_API_KEY` as legacy-compatible bridge env names without suggesting GPTMail is the preferred current product path.
- [ ] No real provider secret values are introduced into code, docs, or test fixtures.
- [ ] Provider/API and settings regression tests pass, plus full project tests if time allows.

## Out Of Scope

- Renaming environment variables, database keys, provider keys, or request fields.
- Removing `outlook_web.services.gptmail` or legacy settings migration logic.
- Redesigning the Settings page layout beyond copy and label cleanup.
