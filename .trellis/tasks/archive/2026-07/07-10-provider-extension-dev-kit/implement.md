# Provider extension developer kit implementation plan

## Checklist

1. Read backend and shared Trellis specs relevant to scripts, provider contracts, logging, and cross-layer readiness.
2. Add or expose a reusable local provider validation helper if needed by both CLI and the new script.
3. Implement `scripts/provider_dev_kit.py` with `scaffold` and `validate` subcommands, JSON/text output, offline validation by default, and secret metadata scanning.
4. Update `docs/provider-onboarding.md` with the recommended dev-kit flow and safety guarantees.
5. Update `scripts/project_readiness_check.py` so the dev-kit script and provider-onboarding documentation are guarded by the readiness gate.
6. Add focused tests for provider dev-kit scaffold, validation, secret-scan behavior, JSON stability, and readiness coverage.
7. Run focused validation and fix failures without broad refactors.
8. Commit the verified task and archive it through Trellis.

## Validation Commands

Run at minimum:

```bash
python -m pytest tests/test_provider_dev_kit.py tests/test_temp_mail_plugin_cli.py tests/test_temp_mail_provider_contract_validation.py tests/test_project_readiness_check.py -q
python scripts/project_readiness_check.py --format json
git diff --check
```

If implementation touches broader provider loading behavior, also run:

```bash
python -m pytest tests/test_temp_mail_provider_plugin_template.py tests/test_temp_mail_plugin_manager.py tests/test_temp_mail_provider_factory.py -q
```

## Risk Points

- Plugin import side effects: keep validation behavior aligned with the existing CLI and document that providers must be import-safe.
- Network calls: keep `probe_options` disabled by default in the new dev-kit validation command.
- Secret reporting: never include matched token values in reports, assertion messages, docs, or examples.
- Readiness check drift: minimal string-contract additions only, with tests updated to keep fixtures realistic.

## Review Gate

Before starting implementation, confirm that this task remains additive and does not include live provider-specific API integrations.
