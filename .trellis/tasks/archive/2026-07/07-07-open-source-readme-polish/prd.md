# Open source landing README polish

## Goal

Make the repository README first screen describe the current product accurately: a unified mailbox platform for Outlook/IMAP accounts, provider-backed temp mailboxes, mailbox pools, and external API automation. The goal is a practical open-source landing improvement, not a full marketing rewrite.

## Background

The current README still opens as a registration-focused Outlook mailbox manager. Recent work has moved the project toward a unified mailbox workspace, provider discovery, provider config files, OpenAPI, external workflows, and onboarding docs. A new visitor should understand those capabilities before scrolling into version history.

## Requirements

- Update the top of `README.md` and `README.en.md` so the first screen names the unified mailbox platform direction.
- Add concise links to the most useful entry points: quick start, external API/provider integration, provider onboarding, browser extension, and screenshots.
- Keep the existing demo, screenshots, version history, and detailed docs intact.
- Do not add unverified claims, fake badges, fake benchmarks, or secret values.
- Keep the copy practical and short. Do not turn the README into a long landing page.

## Acceptance Criteria

- Chinese and English README first screen explain the unified mailbox platform, provider-backed temp mail, and external API value.
- The quick entry links point to existing sections or files.
- Existing detailed setup/API/provider sections remain available.
- Secret scan and markdown link sanity checks pass for touched docs.
