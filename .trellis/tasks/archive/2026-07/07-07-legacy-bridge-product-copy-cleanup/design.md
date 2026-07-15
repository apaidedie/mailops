# Legacy bridge product copy cleanup design

## Boundary

This task changes naming and documentation only. It must not change provider selection semantics, alias normalization, endpoint paths, environment variable names, settings keys, or external API request fields.

## Current Contract

- `provider_catalog._TEMP_PROVIDER_LABEL_OVERRIDES` owns display labels for built-in temp providers in discovery and settings payloads.
- `GPTMAIL_RUNTIME_ALIASES` and deployment-profile alias maps preserve `gptmail`, `legacy_gptmail`, and `temp_mail` compatibility.
- `config.get_temp_mail_base_url()` and `get_temp_mail_api_key_default()` intentionally read old `GPTMAIL_*` env names as the compatibility bridge defaults.
- Settings and target-contract tests assert legacy settings migration and base-url normalization.

## Target Product Semantics

Use `Compatible Temp Mail Bridge` in English-facing machine labels and `兼容临时邮箱桥接` in Chinese UI/docs for the formal product-facing provider label. Keep references to `GPTMAIL_*` only as legacy-compatible environment variable names and alias values.

## Data Flow

Settings/API discovery reads provider catalog labels -> `/api/settings`, `/api/providers`, `/api/external/providers`, `/api/external/capabilities`, `/api/mailboxes.provider_context`, and frontend provider selectors/guides render those labels. Updating the catalog label owner should avoid duplicating label fixes across UI code.

README and `.env.example` must match that contract so external operators see the same wording as API discovery.

## Compatibility

Allowed to keep `gptmail` in alias maps, tests, compatibility env names, old service module names, and low-level migration tests. Not allowed to use GPTMail as the formal label for the compatible bridge family.

## Validation

- Settings contract tests for formal label and legacy env/settings behavior.
- Provider/API tests that assert alias preservation and secret-free discovery.
- Frontend/provider contract tests where labels or guide copy appear.
- Secret scan for accidental real DuckMail/API key values.
