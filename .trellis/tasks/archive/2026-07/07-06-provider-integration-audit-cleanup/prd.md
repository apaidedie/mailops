# Provider integration audit and cleanup

## Goal

Audit the provider integration surface after the recent temp-mail provider and external API command-center work, then fix any low-risk correctness, safety, documentation, or contract drift issues found in the current slice.

This is a lightweight cleanup task. It does not redefine the long-term product goal of becoming a unified Outlook plus temp-mail aggregation service.

## Requirements

- Re-check built-in temp-mail providers and compatibility aliases, including `mail_tm`, `duckmail`, `tempmail_lol`, `emailnator`, `legacy_bridge`, `gptmail`, `legacy_gptmail`, and `temp_mail`.
- Verify discovery surfaces stay aligned: `/api/providers`, `/api/external/providers`, `/api/external/capabilities`, `/api/external/openapi.json`, and `/api/mailboxes` provider context.
- Verify Settings -> API Security external API command-center behavior remains secret-safe and uses placeholder API keys only.
- Check frontend integration-guide rendering, endpoint copy helpers, i18n strings, CSS overflow, and any obvious debug logging or stale copy related to provider onboarding.
- Check README and API docs for obvious provider-list drift or misleading wording introduced by the recent provider additions.
- Fix only contained, low-risk issues that can be verified in this session. Defer broader architecture, UI redesign, and provider implementation expansions to follow-up tasks.
- Do not remove compatibility aliases or change runtime provider selection precedence.
- Do not expose or commit real provider secrets, especially DuckMail bearer tokens.

## Acceptance Criteria

- Targeted static checks pass for changed JavaScript and Python files.
- Provider/API regression tests covering settings, provider discovery, external APIs, unified mailbox catalog, and provider factory pass.
- Secret scans find no real DuckMail token or copied API-key values in repository-visible files.
- Any fixes are covered by existing or new focused tests when behavior changes.
- Remaining non-blocking cleanup opportunities are reported clearly for follow-up.

## Notes

Relevant specs: `.trellis/spec/backend/provider-selection-contract.md` and `.trellis/spec/frontend/quality-guidelines.md`.
