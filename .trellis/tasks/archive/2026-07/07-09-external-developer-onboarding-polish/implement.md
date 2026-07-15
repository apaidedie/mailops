# Implementation Plan

## Checklist

1. Add `docs/project-launchpad.md` with compact product, provider, API, and
   validation guidance.
2. Link the launchpad from the quick-entry block in `README.md` and
   `README.en.md`.
3. Extend `scripts/project_readiness_check.py` with required asset, README link,
   launchpad contract, and secret scan coverage.
4. Update `tests/test_project_readiness_check.py` and community/docs tests to
   cover the launchpad contract.
5. Run focused verification and readiness checks.

## Validation Commands

```powershell
python -m pytest tests\test_project_readiness_check.py tests\test_community_health_docs.py -q
python scripts\project_readiness_check.py
git diff --check
```

## Rollback Points

- If the readiness checker becomes too strict, keep the doc and README link but
  narrow the checker to stable references only.
- If secret scanning flags false positives, update the launchpad text to use
  placeholders instead of loosening the scanner.
