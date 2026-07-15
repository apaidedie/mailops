# Design

## Architecture

`provider_catalog` remains source of truth. Bridge and Cloudflare move to full `config_schema` + `settings_ui` projections, including optional `actions`. Frontend schema panel becomes the only built-in temp-provider settings renderer; specialized static cards are removed or left as non-authoritative empty mounts if needed for temporary DOM compatibility, but values must flow through schema inputs.

## Field contracts

### legacy_bridge / custom_domain_temp_mail

- `temp_mail_api_base_url` (url/text)
- `temp_mail_api_key` (password/secret)
- `temp_mail_domains` (json)
- `temp_mail_default_domain` (text)
- `temp_mail_prefix_rules` (json)

### cloudflare_temp_mail

- `cf_worker_base_url` (url/text)
- `cf_worker_admin_key` (password/secret)
- `cf_worker_domains` (json, readonly)
- `cf_worker_default_domain` (text, readonly)
- `cf_worker_prefix_rules` (json)
- action `sync_domains`: POST `/api/settings/cf-worker-sync-domains`

## Data flow

Catalog → `/api/providers` → frontend cache → schema field/action render → existing `/api/settings` PUT/GET → settings_repo.

CF sync stays on existing endpoint; frontend action handler maps response domains into readonly schema inputs and snapshot state without rewriting unrelated bridge keys.

## Compatibility

- Keep setting key names unchanged.
- Keep secret masking semantics.
- Keep alias normalization for bridge historical names.
- Auto-save on tab leave continues to collect currently rendered schema fields; unselected provider values remain as stored.

## Trade-offs

MVP uses generic schema panel for bridge/CF rather than inventing a second “special actions panel” mode. Actions are declarative catalog metadata, not provider-name switches in JS.
