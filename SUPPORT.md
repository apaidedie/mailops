# Support

Use the docs below before opening an issue. They are the fastest path for most deployment, integration, and provider questions.

## First places to check

- Two-minute project map: `docs/project-launchpad.md`.
- Quick start and deployment: `README.md` or `README.en.md`.
- Release and Docker publishing behavior: `RELEASE.md`.
- External API integration: `docs/external-integration-quickstart.md`.
- Provider onboarding and plugin validation: `docs/provider-onboarding.md`.
- Browser extension usage: `browser-extension/README.md`.

## Opening an issue

Use the bug or feature templates under `.github/ISSUE_TEMPLATE/`. Include enough context for maintainers to reproduce or reason about the issue:

- Version, commit, Docker image tag, or deployment mode.
- Python and Node versions when relevant.
- Whether the issue affects Outlook OAuth, IMAP, mailbox pool, external API, a temp-mail provider, browser extension, or Docker deployment.
- The exact endpoint, command, provider key, or UI page involved.
- Sanitized logs with trace IDs or error codes when available.

Do not include real API keys, provider bearer tokens, refresh tokens, task tokens, mailbox passwords, database files, mailbox exports, screenshots with live mailbox content, or private user data.

## Provider and external API help

For new temp-mail providers, start from `docs/provider-onboarding.md` and validate plugin shape with:

```bash
python web_outlook_app.py validate-provider <provider_key> --file <plugin.py>
```

For external service integration, start with the read-only checks:

```bash
python scripts/project_readiness_check.py
python scripts/external_api_smoke.py --base-url <url> --api-key <your-api-key>
```

The first command checks the repository assets. The second checks a running instance and requires your own deployed API key.

## Support boundaries

Maintainers can help with project bugs, documented setup paths, provider contract issues, and reproducible integration failures. They generally cannot debug third-party mailbox bans, upstream provider outages, private deployment platforms without sanitized logs, or issues that require access to your real secrets or mailbox contents.
