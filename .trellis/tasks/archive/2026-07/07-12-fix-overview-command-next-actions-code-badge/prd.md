# Fix overview command next-actions code badge

## Goal

Replace the literal `TODO` badge on the Dashboard command-center next-actions panel with a stable operator-facing code.

## Confirmed Facts

- Other tiles use short codes such as `MAIL`, `PROV`, `API`.
- The next-actions block currently renders `<span class="ov-card-code">TODO</span>`.

## Requirements

- Use a non-placeholder code badge (e.g. `NEXT`).
- Keep the translated title `下一步动作`.
- Contract test asserts the badge is not `TODO`.

## Acceptance Criteria

- [x] Overview next-actions code badge is not the literal `TODO`.
- [x] Focused tests + `git diff --check` pass.

## Out Of Scope

- Redesigning the command-center layout or action generation backend.
