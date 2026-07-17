# UI Simplify — Workflow B

**Goal:** Clean, scannable MailOps UI for managing purchased Outlook + temp mail, with optional external API. No marketing copy on primary surfaces.

## Product priorities
1. Import / group / browse accounts (primary)
2. Read mail / extract verification codes
3. Optional: configure API key for external projects

## Rules
- No page subtitles, kickers, or “command center” marketing lines on default views
- Form help text: hidden by default (hover/`title` or collapsible “说明” only when needed)
- Advanced filters / diagnostics / API contract tools: collapsed by default
- Groups remain first-class (self-built channel groups)

## Surfaces
| Page | Default | Advanced |
|------|---------|----------|
| Dashboard | 3 KPIs + one next step if needed | Extra tabs stay |
| Unified mailbox | Search + list + preview | Extra filters / diagnostics tab |
| Settings | Labels + fields only | Long hints hidden |
| API security | API key + core toggles | Bundle/smoke/contract collapsed |

## Non-goals
- No backend API contract changes
- No removal of refresh log or pool features
