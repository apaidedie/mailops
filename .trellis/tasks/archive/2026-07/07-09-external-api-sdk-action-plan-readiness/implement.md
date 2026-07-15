# Implementation Plan

## Checklist

1. Add Python action-plan summary helper and `integration-bundle --summary` CLI flag.
2. Add JavaScript equivalent helper and CLI flag.
3. Update Python and JavaScript tests for live bundle summary, fallback summary, output-file behavior, read-only calls, and secret safety.
4. Update `docs/external-integration-quickstart.md` with summary-mode examples.
5. Run targeted checks and fix failures.

## Validation Commands

```powershell
node --check examples\external_api_javascript_client.js
python -m pytest tests\test_external_api_python_client.py -q
node --test tests\external_api_javascript_client.test.js
python scripts\project_readiness_check.py
git diff --check
```

## Risk Points

- Keep the default `integration-bundle` output unchanged for existing scripts.
- Do not leak the CLI API key or provider secret values into summary output.
- Do not let fallback summary imply readiness that older deployments did not explicitly report.
