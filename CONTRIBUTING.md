# Contributing to Outlook Email Plus

Thanks for improving Outlook Email Plus. This project is focused on registration and verification workflows, so changes should keep the app operational, automation-friendly, and safe around credentials.

## Start with the right path

- For user-facing fixes or features, open an issue with the bug or feature template before large changes.
- For external API integration work, read `docs/external-integration-quickstart.md` first.
- For mailbox provider work, read `docs/provider-onboarding.md` first and prefer the plugin contract over provider-specific routes.
- For release or deployment changes, read `RELEASE.md` and keep GitHub Actions gates current.

## Local setup

```bash
python -m venv .venv
pip install -r requirements.txt
python web_mailops_app.py
```

Use `.env.example` as the configuration template. Keep real secrets in your local `.env` or deployment platform, never in committed docs, tests, screenshots, or fixtures.

## Before opening a pull request

Run the checks that match your change. At minimum for integration/provider/docs changes:

```bash
python scripts/project_readiness_check.py
python -m unittest tests.test_ci_readiness_gate_workflows tests.test_project_readiness_check -v
```

For backend or external API changes, also run focused tests around the touched contract. Common examples:

```bash
python -m pytest tests/test_external_api_smoke_script.py tests/test_external_api_python_client.py -q
node --test tests/external_api_javascript_client.test.js
```

For broad backend changes, run the full test suite before asking for review:

```bash
python -m unittest discover -s tests -v
```

## Provider contributions

New temporary mailbox providers should be added through the provider/plugin contract unless there is a strong reason to change core runtime behavior. A provider contribution should include:

- Provider metadata and config schema with no secret default values.
- Clear env/settings keys in `.env.example` or provider docs when needed.
- Contract validation using `python web_mailops_app.py validate-provider <provider_key> --file <plugin.py>`.
- Tests proving provider discovery, readiness, and secret-free payloads.

Provider selection should stay catalog-driven. External callers should discover `/api/v1/external/*` endpoints and use `provider` for pool claims or `provider_name` for task temp-mail creation.

## Pull request expectations

- Keep PRs focused on one behavior, workflow, or documentation area.
- Include tests for new behavior and regression coverage for fixes.
- Update README/docs when changing setup, external API behavior, provider onboarding, or release flow.
- Do not commit generated runtime data, local databases, mailbox exports, credentials, `.env`, screenshots with live mailbox data, or provider/API tokens.
- Use clear commit messages such as `feat: ...`, `fix: ...`, `docs: ...`, `ci: ...`, or `chore: ...`.

## Security and privacy

Do not post or commit API keys, provider bearer tokens, refresh tokens, task tokens, mailbox passwords, database files, or live mailbox contents. See `SECURITY.md` for reporting sensitive issues.
