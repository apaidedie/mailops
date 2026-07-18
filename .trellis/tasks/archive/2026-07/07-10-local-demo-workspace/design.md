# Local Demo Workspace Design

## Boundary

Add a standalone repository helper script at `scripts/seed_demo_workspace.py`. It is an operator/developer onboarding tool, not a runtime route, service, or schema migration.

The script may import `outlook_web.db.init_db()` and `outlook_web.db.create_sqlite_connection()` so it uses the real schema and migration path. It must not instantiate the Flask app, start schedulers, call temp-mail providers, probe networks, or create upstream mailboxes.

## Data Flow

1. Parse CLI arguments.
2. Resolve the target database path. The default is `output/demo/mailops-demo.db`.
3. In dry-run mode, report the resolved path and planned demo rows without creating or mutating the database.
4. For real runs, set safe process env defaults required by `init_db()` only when absent: `SECRET_KEY`, `LOGIN_PASSWORD`, and `SCHEDULER_AUTOSTART=false`.
5. Create the parent directory, optionally delete the target DB and SQLite sidecar files when `--reset` is passed, then call `init_db(database_path=...)`.
6. Open a SQLite connection and upsert synthetic demo rows.
7. Print either text or JSON with the database path, row counts, login hint, and startup command.

## Seed Contract

The seed rows are tagged with stable demo markers:

- Email domains: `demo.local`, `temp.demo.local`, and `mail.example`.
- Group name: `Demo Workspace`.
- Audit operator: `demo-seed`.
- Usage consumer keys: `demo-webhook`, `demo-browser-extension`, `demo-ci-worker`.

Before inserting seed rows, the script deletes only rows matching those stable demo markers. This keeps repeated runs deterministic while avoiding unrelated data when an operator intentionally targets an existing database.

Seeded surfaces:

- Accounts: Outlook/Graph, IMAP, and pool lifecycle examples.
- Temp mailboxes: DuckMail/mail.tm-compatible, TempMail.lol, Emailnator, and Cloudflare Worker style local rows.
- Temp messages: cached verification and onboarding messages.
- Pool: account claim logs and project usage rows.
- Overview: verification extract logs, refresh run, audit activity, and external API usage rows.

## Secret Safety

All credentials in seeded account rows are placeholders that cannot authenticate anywhere. The script avoids values that match repository secret scanners, including real DuckMail bearer-token shape, `Bearer ...`, `sk-...`, GitHub tokens, Google API keys, JWTs, and long API-key-looking strings.

The demo script does not print or persist real environment values. If it needs a `SECRET_KEY` for local encryption during schema initialization, it uses a fixed demo-only value only when the process does not already define one.

## Documentation And Readiness

`docs/project-launchpad.md`, `README.md`, and `README.en.md` should add a concise local demo command near existing first-run/readiness instructions.

`scripts/project_readiness_check.py` should require and secret-scan `scripts/seed_demo_workspace.py`, and its launchpad contract should fail if the demo path disappears from the two-minute trial path.

## Compatibility

No schema version changes are required. The script uses current schema fields and should tolerate future additive columns by writing only known columns.

Default DB output lives under `output/`, which is already appropriate for generated local artifacts.

## Rollback

Rollback is deleting the new script/docs/tests/readiness edits. Generated demo DB files are local artifacts and are not committed.
