# External integration onboarding kit implementation plan

## Checklist

1. Inspect the provider documentation contract and existing docs links.
2. Add the external integration quickstart with placeholder-only examples.
3. Implement `scripts/external_api_smoke.py` with standard-library HTTP calls and pure validation helpers.
4. Add unit tests that mock fetches and validate success/failure behavior.
5. Link README and documentation discovery to the quickstart when compatible with existing contracts.
6. Run focused tests, compile the script, run help output, diff check, and secret scan.
7. Commit, archive, and record the session.

## Validation Commands

- `python -m pytest tests/test_external_api_smoke_script.py -q -rs`
- `python scripts/external_api_smoke.py --help`
- `python -m py_compile scripts/external_api_smoke.py`
- Existing discovery contract test if provider documentation contract changes: `python -m pytest tests/test_external_api.py -q -rs -k "capabilities_returns_feature_list_and_audits or openapi_contract_exposes_external_api_paths_and_security"`
- `git diff --check`
- Secret scan over changed files.

## Risk

- The smoke checker must stay read-only by default, otherwise a simple validation command could consume mailbox pool state.
- Documentation examples must use placeholders and avoid embedding any real user-provided provider token.
- README should link, not duplicate another long API reference.
