# Security Policy

Outlook Email Plus handles mailbox accounts, API keys, provider credentials, OAuth refresh tokens, task lifecycle handles, and message content. Treat reports and reproduction material accordingly.

## Reporting a vulnerability

If GitHub private vulnerability reporting is enabled for this repository, use that channel first. If it is not available, open a minimal public issue that says you have a security report and ask for a private contact path. Do not include exploit details or secrets in the public issue.

When a private channel is available, include:

- Affected version, commit, or deployment mode.
- A concise impact description.
- Reproduction steps with placeholder values.
- Whether the issue affects external API keys, provider credentials, mailbox access, token storage, public-mode restrictions, or Docker/deployment behavior.

## Do not disclose secrets publicly

Never post these values in public issues, pull requests, logs, screenshots, or examples:

- External API keys and `X-API-Key` values.
- Provider API keys or bearer tokens such as `DUCKMAIL_BEARER_TOKEN`, `GPTMAIL_API_KEY`, `TEMPMAIL_LOL_API_KEY`, `EMAILNATOR_API_KEY`, or Cloudflare Worker admin keys.
- OAuth refresh tokens, access tokens, JWTs, task tokens, claim tokens, consumer keys, mailbox passwords, SMTP passwords, database files, mailbox exports, or live message content.

Use placeholders such as `<your-api-key>`, `<provider-token>`, or `example@example.com` in public material.

## Maintainer triage expectations

Maintainers should acknowledge credible reports, reproduce privately, assess affected versions, and avoid requesting real secrets. Fixes should include tests or readiness checks where practical, and release notes should describe impact and upgrade guidance without publishing exploit-ready details before users have a reasonable update path.

## Local checks

Before publishing security-sensitive integration or provider changes, run:

```bash
python scripts/project_readiness_check.py
```

This gate scans checked-in integration docs, examples, scripts, and config templates for obvious secret values, but it is not a substitute for careful review.
