# Open source community health docs

## Goal

Add practical community health documentation so Outlook Email Plus looks and works like a credible open-source project for users, contributors, provider authors, and security reporters.

## User Value

New users should know where to get help and how to report issues. Contributors should know the local checks expected before a pull request. Provider authors should have a short path to add or validate new mailbox providers. Security reporters should have a clear private-reporting policy and know not to paste secrets into public issues.

## Confirmed Facts

The repository already has README files, release docs, issue templates, PR template, license, CI workflows, external integration docs, provider onboarding docs, and a local readiness checker. It does not currently expose top-level `CONTRIBUTING.md`, `SECURITY.md`, or `SUPPORT.md` files, which GitHub treats as community health signals and which are useful for a project targeting broad adoption.

## Requirements

Add concise, actionable community docs. `CONTRIBUTING.md` must cover local setup, branch/commit expectations, tests/readiness gates, docs expectations, external API/provider contribution guidelines, and what not to include in PRs. `SECURITY.md` must cover supported reporting channels when no private advisory channel is configured, secret-handling guidance, public issue restrictions, and maintainer triage expectations. `SUPPORT.md` must direct users to docs, issue templates, required diagnostic details, and boundaries for deployment/provider support. README and README.en should link to the new docs without turning the top section into clutter.

## Acceptance Criteria

- [x] `CONTRIBUTING.md` exists and references setup, tests, `python scripts/project_readiness_check.py`, provider onboarding, external integration docs, and PR expectations.
- [x] `SECURITY.md` exists and clearly tells users not to post API keys, provider bearer tokens, refresh tokens, task tokens, passwords, database files, or live mailbox data in public issues.
- [x] `SUPPORT.md` exists and routes users to quick start, external integration, provider onboarding, issue templates, and required diagnostics.
- [x] README and README.en link the new community docs from the start section or nearby project metadata.
- [x] A lightweight test verifies the community health docs and README links stay present.

## Out of Scope

This task does not create GitHub Discussions, change repository settings, add a Code of Conduct, change runtime behavior, or push to GitHub.
