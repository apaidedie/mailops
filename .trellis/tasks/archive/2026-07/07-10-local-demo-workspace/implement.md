# Implementation Plan

## Checklist

1. Add `scripts/seed_demo_workspace.py` with CLI parsing, dry-run, reset, JSON/text output, default isolated DB path, and deterministic demo seeding.
2. Add focused tests for the seed script:
   - dry-run does not create a database.
   - reset run creates the schema and expected demo rows.
   - repeated run stays deterministic for stable demo inventory.
   - JSON output exposes the startup command and row counts without secret-looking values.
3. Update `scripts/project_readiness_check.py` to require and secret-scan the demo script and require launchpad demo instructions.
4. Update `tests/test_project_readiness_check.py` fixtures and assertions for the new readiness contract.
5. Update `docs/project-launchpad.md`, `README.md`, and `README.en.md` with concise local demo instructions.
6. Run focused validation, then the repository readiness gate.

## Validation Commands

```bash
python -m pytest tests/test_seed_demo_workspace.py tests/test_project_readiness_check.py -q
python scripts/seed_demo_workspace.py --dry-run --format json
python scripts/seed_demo_workspace.py --reset --format json
python scripts/project_readiness_check.py --format json
git diff --check
```

## Risk Points

- `init_db()` requires `SECRET_KEY`; the script must set a demo-only fallback before importing encryption-dependent behavior.
- Existing databases may contain real data; deletion must be tightly limited to demo markers unless `--reset` deletes the target file the operator explicitly selected.
- Docs and script contents must avoid token-like literals that trip the readiness secret scan.

## Rollback Points

- Before editing readiness gate: the script can stand alone with tests.
- Before docs edits: script/test changes can be validated independently.
- If readiness changes cause broad failures, keep the script and docs but defer the readiness-gate expansion only after documenting why.
