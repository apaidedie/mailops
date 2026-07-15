# Database Guidelines

The project uses SQLite directly through `sqlite3`; there is no ORM. Database behavior is intentionally explicit so migrations, encryption, and compatibility with existing single-file deployments stay predictable.

## Connection Lifecycle

- Use `outlook_web.db.get_db()` inside request/app contexts. It stores the connection on `flask.g` and uses `sqlite3.Row` for row access.
- `create_sqlite_connection()` sets `PRAGMA foreign_keys = ON` and `PRAGMA busy_timeout = 5000`; do not create ad hoc raw connections unless you need an isolated script/test path.
- `register_db(app)` wires teardown cleanup. Do not close the shared request connection manually in controllers/services.

## Query Patterns

- Repositories own persistence queries. Put new CRUD/query behavior under `outlook_web/repositories/<resource>.py` unless the query is a cross-source read model owned by a service, such as `services/mailbox_catalog.py`.
- Use parameterized SQL with `?` placeholders. Build dynamic `WHERE` clauses by appending trusted SQL snippets plus a separate `params` list, as in `repositories/accounts.py`.
- Convert `sqlite3.Row` objects to dictionaries at repository or service boundaries before returning JSON-facing data.
- Batch related lookups when practical. `repositories/accounts._load_tags_by_account_ids()` is the current pattern for avoiding N+1 tag queries.
- Normalize pagination inputs with bounded integers. Typical limits cap at 200 or a feature-specific maximum.

## Transactions And Commits

- Repository write functions should commit after successful mutation unless the caller explicitly owns a multi-step transaction.
- `db.py` migrations use `BEGIN IMMEDIATE`, savepoints, migration trace IDs, and `schema_migrations` records. Follow that pattern for schema upgrades.
- Audit writes intentionally swallow failures so audit logging does not break the main flow; do not copy that pattern for primary data writes.

## Migrations

- Schema version is centralized in `outlook_web/db.py` as `DB_SCHEMA_VERSION`. Increment it when adding or changing schema.
- Migrations must be idempotent for fresh databases and older databases. Use `CREATE TABLE IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`, and defensive column/index checks where needed.
- Add a short version comment near `DB_SCHEMA_VERSION` describing the migration.
- Add migration tests for schema changes. Existing examples include `tests/test_db_schema_v22_pool_project_reuse.py`, `tests/test_db_schema_v23_overview.py`, and `tests/test_db_migration_task_token_unique.py`.

## Secrets And Encryption

- Account credentials are stored encrypted. Use repository helpers such as `_decrypt_account_field()` and crypto helpers from `outlook_web.security.crypto` instead of exposing raw encrypted values to controllers or UI payloads.
- Public discovery/readiness payloads must not include mailbox passwords, refresh tokens, API keys, bearer tokens, task tokens, consumer keys, provider JWTs, or decrypted credential values.
- Provider configuration docs and manifests may expose secret key names, but secret values must be blank or absent.

## Naming Conventions

- Table and column names are snake_case.
- Timestamps are stored as SQLite timestamp text or numeric epoch fields depending on the existing table contract. Preserve a table's current style when adding related columns.
- Index names should start with `idx_` and include the table plus purpose, for example `idx_temp_emails_task_token_unique`.

## Common Mistakes

- Adding direct SQL to controllers because it is faster. Put persistence in a repository or a service-owned read model.
- Forgetting to update `DB_SCHEMA_VERSION` and migration tests when adding a column.
- Building SQL with interpolated user input. Only trusted column/order snippets may be interpolated after normalization; values must use placeholders.
- Returning decrypted credentials or `meta_json` token fields from inventory/readiness endpoints.
