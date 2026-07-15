# External integration manifest documentation

## Goal

Update the public README integration guidance so external projects discover and use the new `integration_manifest` contract instead of reverse-engineering `provider_integration_guide` or Settings UI snippets.

## Confirmed Facts

- `GET /api/external/capabilities`, `GET /api/external/providers`, authenticated `GET /api/providers`, and OpenAPI `x-capabilities` now expose top-level `integration_manifest`.
- The manifest is secret-safe: API keys use `<your-api-key>`, provider secret key names may appear, and provider secret values remain empty.
- README.md and README.en.md still describe `provider_integration_guide`, `deployment_profile`, and `selection_policy`, but do not mention `integration_manifest`.
- This is documentation-only work. Runtime contracts and tests were already implemented in `c30a4f1`.

## Requirements

- Update README.md and README.en.md to mention `integration_manifest` in the external provider discovery guidance.
- Explain that `integration_manifest` is the preferred machine-readable starter contract for external projects, while `provider_integration_guide` remains the detailed per-provider guide.
- Document the manifest's API key placeholder, discovery sequence, provider request fields, source priority, env/config hints, and secret-safety behavior.
- Keep the wording concise and aligned across Chinese and English READMEs.
- Do not include real provider tokens, masked secret values, or user-specific secrets.

## Acceptance Criteria

- README.md explains that external projects can read `integration_manifest` from `/api/external/capabilities`, `/api/external/providers`, or OpenAPI `x-capabilities`.
- README.en.md contains the same guidance in English.
- Both READMEs state that secret env/settings values are emitted as empty values and API keys use `<your-api-key>`.
- Token and debug scans still pass.

## Out of Scope

- Changing runtime API behavior.
- Adding SDK generation or new UI in this task.
