# Version metadata consistency

## Goal

Align project version metadata and README stable-version claims with the runtime application version so open-source users, update checks, and UI version labels describe the same release line.

## Confirmed Facts

- Runtime app version is defined in `mailops/__init__.py` as `2.7.0`.
- `package.json` currently reports `2.1.0`.
- `README.md` and `README.en.md` currently claim stable version `v2.2.2`.
- The Flask app injects `mailops.__version__` into the UI and system endpoints.
- There is no product decision needed from the user; the runtime application version is the authoritative source for this cleanup.

## Requirements

- Keep `mailops.__version__` as the single source of truth for the current application version.
- Update npm metadata (`package.json` and root project entries in `package-lock.json`) and both README stable-version claims to match the runtime app version.
- Add a regression test that fails when these version strings drift again.
- Do not change release notes, feature claims, application behavior, APIs, database schema, or deployment configuration.

## Acceptance Criteria

- A test asserts npm package metadata equals `mailops.__version__`.
- The same test asserts the stable version shown in `README.md` and `README.en.md` equals `v{mailops.__version__}`.
- Focused version-metadata test passes.
- `git diff --check` passes without whitespace errors.

## Notes

- Keep `prd.md` focused on requirements, constraints, and acceptance criteria.
- Lightweight tasks can remain PRD-only.
- For complex tasks, add `design.md` for technical design and `implement.md` for execution planning before `task.py start`.
