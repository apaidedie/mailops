# Backend Directory Structure

This project is a Flask application with a deliberately split backend. Keep new work inside the existing layer boundaries so external API, provider, and UI contracts do not drift.

## Top-Level Shape

```text
mailops/
  app.py                 # Flask app factory, middleware, blueprint registration
  config.py              # env/config-file/settings access helpers
  db/                    # package: connection, schema migrations, sensitive migrate
  errors.py              # shared API error payload helpers and sanitization
  audit.py               # audit-log persistence helpers
  routes/                # Blueprint construction and URL registration only
  controllers/           # Flask request handlers (packages for large domains)
  services/              # business contracts, provider integration, mailbox logic
  repositories/          # SQLite CRUD and persistence projections
  middleware/            # request/response middleware and error handlers
  security/              # auth, CSRF, crypto, external API guards
tests/                   # pytest/unittest contract, regression, and integration tests
scripts/                 # local readiness, smoke, healthcheck, release helpers
docs/                    # public integration and provider docs
```

## Layer Ownership

- `routes/*.py` owns URL registration only. Route files create a `Blueprint` and bind controller callables. They must not import services, repositories, or `mailops.db`; this is enforced by `tests/test_module_boundaries.py`.
- `controllers/` owns HTTP concerns: reading `request`, applying auth decorators, validating request bodies, calling services, writing audit events, and returning JSON/envelope responses. Large domains are packages with thin `__init__.py` re-exports:
  - `controllers/accounts/` — list, crud, batch, export, refresh, helpers
  - `controllers/settings/` — read, update, test helpers
  - `controllers/emails/` — mailbox + external message handlers
  - `controllers/system/` — health, deploy/update, external docs handlers
  Smaller controllers may remain single modules.
- `services/*.py` (and service packages) own business behavior and machine-readable contracts. Examples:
  - `provider_catalog/` (`constants`, `bridge`, `endpoints`, `catalog`, `selection`, `integration`, `capabilities`, `health`; thin `_impl` re-export hub)
  - `external_api/` (`constants`, `errors`, `access`, `messages`, `probes`, `verification`, `upstream`, `openapi`; shim `external_api_openapi.py` re-exports OpenAPI entry)
  - `account_import_export.py`, `mailbox_catalog.py`, `temp_mail_service.py`, `pool.py`
- `repositories/*.py` owns direct SQLite access for a resource. Repositories may import `mailops.db` and security crypto helpers, but not Flask, routes, or services.
- `db/` owns schema creation and migrations (`constants`, `connection`, `schema`, `sensitive`). Public import path remains `from mailops.db import get_db, init_db, ...`. Do not create migration DDL in controllers or services.
- `config.py` owns environment/config-file access. Do not call `os.getenv()` across feature code when a config helper exists or should exist.

## Adding A Backend Feature

1. Add or extend a service contract first when behavior is reusable across API, UI, docs, or smoke checks.
2. Add repository functions only for persistence access. Keep them small and parameterized.
3. Add controller handlers that compose request validation, service calls, and response envelopes. Prefer a new submodule under an existing controller package when the domain is already packaged.
4. Register routes in the matching `mailops/routes/*.py`. For external API routes, use `add_external_api_url_rule()` so canonical `/api/v1/external/*` mounts correctly.
5. Add tests at the contract surface: service tests for pure behavior, API tests for envelopes/auth/status codes, readiness/docs tests for public integration surfaces.

## Naming Conventions

- Backend files use snake_case module names.
- Controller functions use `api_*` for JSON API handlers and describe the route behavior, for example `api_external_get_providers`.
- Service helpers that return public machine contracts use `get_*_contract`, `get_*_summary`, `get_*_manifest`, or `*_metadata` names.
- Repository functions should read like persistence operations: `load_*`, `create_*`, `update_*`, `delete_*`, `query_*`.
- Constants that define public API fields, endpoint paths, or provider keys belong beside the service contract that owns them.
- Package `__init__.py` re-exports symbols heavily imported by tests and routes to keep public paths stable.

## Examples To Follow

- External provider discovery: `routes/external_temp_emails.py` registers paths, `controllers/external_temp_emails.py` handles HTTP/auth/audit, and `services/provider_catalog` owns the readiness, routing, capability, and integration-guide contracts (`from mailops.services.provider_catalog import ...` remains the stable public path).
- External runtime API: `services/external_api` package; OpenAPI via `services/external_api/openapi.py` or shim `from mailops.services.external_api_openapi import get_external_api_openapi_contract`.
- Account import/export pure logic: `services/account_import_export.py`; `controllers/accounts` re-exports `_detect_line_type` / `_build_export_text` for existing tests.
- Unified mailbox directory: `services/mailbox_catalog.py` owns filtering/facets/action contracts, and `services/mailbox_directory_contract.py` owns the fixed directory schema metadata.
- Settings/config work: `config.py` reads env/config-file values, `repositories/settings.py` persists runtime settings, and controllers should not duplicate config-file parsing.

## Forbidden Patterns

- Do not import `mailops.services`, `mailops.repositories`, or `mailops.db` from `mailops/routes`.
- Do not import Flask, routes, or services from repositories.
- Do not rebuild provider selection, endpoint maps, quickstarts, or readiness projections in controllers, frontend code, docs scripts, or smoke scripts. Call the provider catalog helpers.
- Do not add provider-specific routes for new temp-mail providers when the plugin/provider catalog contract can represent the provider.
- Do not leave a monofile and package with the same import name side by side (`db.py` vs `db/`).
