# Design

## Architecture

`outlook_web.config` owns environment parsing and origin validation. A new `outlook_web/cors_config.py` module owns the safe discovery contract and Flask-CORS registration. `create_app()` delegates to `configure_external_api_cors(app)`.

`provider_catalog.get_external_api_capabilities_contract()` copies the safe CORS contract into `cors`. `get_external_api_readiness_summary()` projects the same contract into `cors`, so the integration bundle includes it through `readiness.external_api.cors` without rebuilding policy elsewhere.

## Configuration Contract

- `EXTERNAL_API_CORS_ORIGINS`: exact HTTP(S) origins separated by commas or newlines.
- `EXTERNAL_API_CORS_ALLOW_CHROME_EXTENSION`: boolean, default true.
- Empty origins plus extension enabled -> extension-only mode.
- Empty origins plus extension disabled -> browser CORS disabled.
- Invalid values are ignored and counted; raw invalid values are not exposed.

## Safe Discovery Contract

Fields: `status`, `enabled`, `mode`, `allowed_origins`, `allowed_origin_count`, `invalid_origin_count`, `chrome_extension_enabled`, `credentials`, `methods`, `allowed_headers`, `exposed_headers`, `max_age_seconds`, and `environment` key names.

Status/mode values describe browser CORS only and do not change server-to-server readiness. Exact origins are deployment metadata, not secrets, and are visible only through API-key-protected external discovery or authenticated admin projections.

## Security Boundaries

Reject `*`, credentials in URLs, paths other than `/`, query strings, fragments, and schemes other than HTTP(S). Keep `supports_credentials=False`. CORS only controls browser response access; API-key guards remain authoritative for every external endpoint.

## Compatibility And Rollback

The default keeps extension behavior unchanged. Operators can return to extension-only behavior by clearing `EXTERNAL_API_CORS_ORIGINS`, or disable all browser CORS by also setting `EXTERNAL_API_CORS_ALLOW_CHROME_EXTENSION=false`.
