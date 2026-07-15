# External developer onboarding polish

## Goal

Create a short project launchpad that lets a GitHub visitor, operator, or external
integration developer understand the current product shape in under two minutes:
what mailbox sources are supported, how to run the project, how to connect through
the external API, and where to validate readiness before using it in another
service.

## Background

- The repository already has detailed Chinese and English READMEs, external API
  quickstart docs, provider onboarding docs, starter clients, and a local
  readiness checker.
- The current gap is scanability, not missing deep documentation. New users must
  read multiple long sections before they can tell whether the project fits their
  use case.
- The project direction is a unified mailbox aggregation service combining
  Outlook/Graph, IMAP, mailbox pools, provider-backed temp mailboxes, plugins,
  and controlled external APIs.
- This task is a focused onboarding slice. It must improve public presentation and
  integration confidence without changing mailbox runtime behavior.

## Requirements

- Add a concise `docs/project-launchpad.md` that acts as the first-stop map for:
  product positioning, supported mailbox sources, shortest local/deployment path,
  external API integration path, provider extension path, and validation commands.
- Link the launchpad prominently from both `README.md` and `README.en.md` near the
  existing quick-start entry points.
- Keep the launchpad secret-safe. It may mention secret key names, but it must not
  contain real API keys, bearer tokens, passwords, JWTs, refresh tokens, task
  tokens, consumer keys, or provider secret values.
- Keep all external API references on canonical `/api/v1/external/*` routes while
  documenting `/api/external/*` only as legacy compatibility when needed.
- Extend `scripts/project_readiness_check.py` and tests so the launchpad becomes a
  required integration asset with required references to the existing quickstart,
  provider guide, readiness checker, integration bundle, starter clients, and
  provider/plugin extension path.
- Do not add a new frontend framework, runtime dependency, or provider-specific
  route.

## Acceptance Criteria

- `docs/project-launchpad.md` exists and is linked from both READMEs.
- The launchpad names the unified mailbox model and covers Outlook/Graph, IMAP,
  mailbox pool, built-in temp-mail providers, Cloudflare Worker temp mail, and
  plugin providers.
- The launchpad points external consumers to `/api/v1/external/integration-bundle`,
  `/api/v1/external/capabilities`, `/api/v1/external/docs`, OpenAPI, and the
  starter clients.
- The launchpad includes safe validation commands for local readiness and live
  external smoke checks.
- The local project readiness checker fails if the launchpad is missing or drifts
  away from the required integration/onboarding references.
- Focused docs/readiness tests pass.

## Out Of Scope

- Runtime provider behavior changes.
- UI layout or browser-rendered Settings changes.
- Full rewrite of existing README sections.
- Publishing, pushing, or opening a pull request.
