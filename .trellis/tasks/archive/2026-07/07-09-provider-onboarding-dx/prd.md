# Provider Onboarding DX

## Goal

Make third-party temp-mail provider onboarding safer and easier by tightening the provider extension contract and documenting the validated happy path from scaffold to production enablement.

## Background

The project already has a temp-mail provider plugin architecture, a scaffold template, CLI validation, provider discovery contracts, and onboarding documentation. The current guide says providers must inherit `TempMailProviderBase`, but `validate_temp_mail_provider_class()` primarily checks names, metadata, config schema, and required methods. A class that only happens to define those methods can be reported as structurally valid even though it bypasses the base class contract the rest of the platform expects.

## Requirements

- The contract validator must reject provider classes that do not inherit `TempMailProviderBase`.
- The validation payload must keep the existing shape and remain secret-free.
- The issue must be machine-readable through a stable issue code so CLI/API/discovery consumers can surface the same failure consistently.
- Existing valid built-in providers, scaffolded providers, and the checked-in template must continue to validate as `valid`.
- Tests that intentionally use legacy loose provider shapes for catalog compatibility may still receive catalog rows, but their contract validation should clearly report the stricter invalid status.
- Onboarding documentation must tell plugin authors that inheritance is a hard validation gate and that `validate-provider` is the readiness check before enabling routing.

## Acceptance Criteria

- [ ] `validate_temp_mail_provider_class()` returns `status=invalid`, `valid=false`, and an explicit issue code for non-`TempMailProviderBase` classes.
- [ ] The issue is included in `contract_validation_summary()` / provider catalog projections without leaking secrets.
- [ ] The template and scaffold tests still prove generated providers inherit the base class and validate successfully.
- [ ] CLI/API tests cover non-base providers failing validation through the same contract path.
- [ ] `docs/provider-onboarding.md` and the Chinese plugin guide describe the base-class requirement and validation command sequence.
- [ ] Focused provider contract/plugin tests pass.
