# External API docs UX

## Goal

Upgrade the authenticated external API docs page into a polished integration
console that helps external developers understand authentication, discovery,
provider selection, mailbox-session workflow, and endpoint coverage quickly.

## Background

- The project already exposes `GET /api/v1/external/docs` as a self-contained
  HTML page generated from the live OpenAPI contract.
- The UI stack detector found no framework or component-library dependency for
  this page; `mailops/services/external_api_docs.py` owns the HTML/CSS.
- Current tests verify auth, canonical/legacy docs discovery, secret redaction,
  and core endpoint visibility.
- The long-term project goal is a professional unified mailbox aggregation
  service with strong external API ergonomics.

## UI Brief

- Audience: integration developers and operators connecting registration
  workers, batch jobs, and automation services.
- Primary workflow: inspect auth requirements, discover the recommended API
  sequence, copy the mailbox-session mental model, and browse endpoint groups.
- Product archetype: operational SaaS / technical integration console.
- Visual direction: dense but calm, precise hierarchy, restrained non-monotone
  palette, no decorative hero, no new JavaScript or third-party assets.
- Constraints: keep the page self-contained, generated from OpenAPI data,
  responsive on mobile and desktop, secret-safe, and authenticated.

## Requirements

- Improve first-viewport information architecture so the page reads as an
  integration dashboard rather than a plain contract list.
- Preserve all existing security and secret-redaction guarantees.
- Keep the implementation in `external_api_docs.py`; do not add a frontend
  framework, network assets, or external CSS/JS dependencies.
- Add visible workflow/health/coverage cues from existing OpenAPI/capabilities
  data without changing API response contracts.
- Maintain responsive behavior for desktop and narrow mobile widths.
- Update tests to pin the new high-value UI sections and prevent regressions.

## Acceptance Criteria

- [x] Authenticated docs page renders a hero/summary area with API version,
      canonical prefix, endpoint count, and auth/secret policy cues.
- [x] The page exposes clear sections for discovery workflow, mailbox session
      workflow, provider selection, and endpoint catalog.
- [x] Endpoint rows still include method, path, summary, operation ID, request
      schema, and response schema where available.
- [x] HTML contains no API keys, provider tokens, refresh tokens, task tokens,
      consumer keys, or realistic bearer token leaks.
- [x] Mobile CSS keeps panels/tables readable without overflow-prone fixed
      layout assumptions.
- [x] Targeted docs/OpenAPI/external API tests pass.

## Out of Scope

- Changing external API endpoint behavior, payload shapes, or auth rules.
- Adding client-side JavaScript, live try-it-out calls, or new dependencies.
- Redesigning the main admin UI.
