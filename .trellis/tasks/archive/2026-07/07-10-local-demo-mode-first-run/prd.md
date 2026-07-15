# Local demo mode first-run experience

## Goal

Make the locally seeded demo workspace obvious and useful on first run so a GitHub visitor or operator can open the app, understand that the data is synthetic, and jump directly into the most representative product surfaces without reading setup docs first.

## Background

- The demo seed command creates an isolated SQLite database at `output/demo/outlook-email-plus-demo.db` with synthetic Outlook, IMAP, temp-mail, verification, pool, and external API usage rows.
- The current app can run against that database, but the authenticated workspace does not visibly indicate demo mode or guide users toward the unified mailbox, temp-mail, and external API surfaces.
- The bootstrap API already hydrates layout/polling settings and is the right contract boundary for safe page-shell metadata.

## Requirements

- Detect the local demo workspace from the configured database path without creating startup side effects or probing external services.
- Add a secret-safe `demo_workspace` object to `/api/bootstrap` only when the configured database path matches the default local demo database.
- Do not expose absolute filesystem paths, provider bearer tokens, API keys, task tokens, claim tokens, mailbox passwords, or live mailbox content in the bootstrap payload.
- Render a restrained in-app demo strip in the authenticated workspace when demo mode is enabled.
- The strip must explain that the workspace uses synthetic demo data and provide quick actions for the core evaluation flows: overview, unified mailbox, temp mailboxes, external API operations, and provider settings.
- Quick actions must use existing navigation and tab behavior rather than adding a second router or duplicating feature logic.
- The strip must be responsive, keyboard-accessible, and visually consistent with the dense operational dashboard style.
- The default non-demo app must not show the demo strip or alter bootstrap behavior beyond a safe disabled `demo_workspace` contract.

## Acceptance Criteria

- [ ] `/api/bootstrap` returns a safe `demo_workspace.enabled=true` payload when `DATABASE_PATH` points to `output/demo/outlook-email-plus-demo.db`.
- [ ] `/api/bootstrap` returns `demo_workspace.enabled=false` for ordinary databases.
- [ ] The authenticated page has a stable demo-strip mount point and frontend renderer that consumes the bootstrap payload defensively.
- [ ] Demo quick actions navigate to the intended existing pages/tabs without reading credential form fields or provider secrets.
- [ ] Frontend contract tests assert DOM hooks, JS helper names, CSS hooks, secret-safety constraints, and responsive selectors.
- [ ] Backend tests cover enabled and disabled bootstrap payloads.
- [ ] Browser QA verifies the running demo on desktop and mobile with no page-level horizontal overflow and visible demo strip.

## Notes

- UI brief: audience is an operator/evaluator testing a mailbox aggregation service; product archetype is operational SaaS; source of truth is the existing Flask/static JS/CSS workspace and local demo seed contract; acceptance requires rendered desktop/mobile checks.
- Art direction: calm data-dense operations UI, restrained blue/action accents from existing tokens, no marketing hero and no nested cards.
