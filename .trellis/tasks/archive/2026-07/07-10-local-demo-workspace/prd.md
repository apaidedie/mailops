# Local demo workspace and first-run kit

## Goal

Give operators, GitHub visitors, and local developers a safe way to experience the unified mailbox product without real Outlook, IMAP, temp-mail, or external API credentials. The demo kit should make the project feel usable immediately: unified mailbox inventory, temp-mail messages, mailbox-pool state, verification extraction history, and external API operations should all have realistic local data.

This increment supports the long-term product goal by improving first-run confidence and showing the value of a combined Outlook/IMAP/temp-mail/external-API workspace before a user has configured live providers.

## Confirmed Facts

- The app stores runtime data in SQLite via `mailops.db.init_db()` and the `DATABASE_PATH` environment variable.
- Current schema includes the demo-relevant tables: `accounts`, `temp_emails`, `temp_email_messages`, `account_claim_logs`, `account_project_usage`, `verification_extract_logs`, `external_api_consumer_usage_daily`, `audit_logs`, and `refresh_runs`.
- `docs/project-launchpad.md` is the current two-minute onboarding map and is validated by `scripts/project_readiness_check.py`.
- The local readiness gate is read-only; demo seeding must remain a separate explicit command.

## Requirements

- R1. Add a local-only demo seed command under `scripts/` that defaults to a separate demo SQLite database, not the production `data/outlook_accounts.db` path.
- R2. The seed command must be idempotent: repeated runs update or replace the same demo rows without duplicating accounts, temp mailboxes, messages, usage rows, or logs indefinitely.
- R3. Seed data must cover the core product surfaces: Outlook/Graph-style account, generic IMAP account, temp-mail provider mailboxes, pool inventory/lifecycle history, cached temp messages, verification extraction stats, and external API usage stats.
- R4. Seed data must be obviously synthetic and secret-safe. It must not contain real API keys, bearer tokens, refresh tokens, mailbox passwords, task tokens, claim tokens, JWTs, provider secrets, or production-looking credentials.
- R5. The command output must tell the operator exactly which database was written and how to start the app against it.
- R6. Public onboarding docs must mention the demo path near the first-run instructions without replacing the real provider configuration docs.
- R7. The readiness gate/tests must prevent the demo script and docs from drifting or accidentally containing secret-looking values.

## Acceptance Criteria

- [ ] `python scripts/seed_demo_workspace.py --reset --format json` succeeds from the repository root and writes a separate demo database by default.
- [ ] Running the seed command twice remains deterministic and does not duplicate stable demo inventory.
- [ ] The seeded database has at least one Outlook account, one IMAP account, multiple temp-mail provider rows, cached temp messages, verification logs, pool claim logs, and external API usage rows.
- [ ] The command has a dry-run mode that reports the target path without mutating the database.
- [ ] `docs/project-launchpad.md`, `README.md`, and `README.en.md` document the local demo path and show placeholder-only commands.
- [ ] `scripts/project_readiness_check.py` treats the demo script as a required, secret-scanned onboarding asset.
- [ ] Focused tests cover the demo script behavior and readiness-gate contract.

## Notes

- Out of scope: live provider probes, creating real upstream mailboxes, changing database schema, redesigning dashboard UI, and embedding API keys in demo configuration.
