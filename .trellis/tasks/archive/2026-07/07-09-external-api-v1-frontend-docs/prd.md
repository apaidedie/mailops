# External API v1 frontend docs canonical

## Goal

Make the externally visible onboarding surfaces follow the new canonical `/api/v1/external/*` contract so new integrators see the stable versioned API by default, while preserving `/api/external/*` as documented legacy compatibility.

This completes the product-facing half of the previous backend alias work: discovery/OpenAPI already expose v1 as canonical, but Settings UI starter snippets, smoke examples, README copy, and quickstart docs still contain legacy fallbacks that can steer new clients to the old prefix.

## Confirmed Facts

- Backend discovery now treats `/api/v1/external/*` as canonical and exposes `/api/external/*` through compatibility metadata.
- `static/js/main.js` still has hardcoded legacy fallback endpoint maps, smoke checks, and degraded-state detail copy.
- `templates/index.html` and `static/js/i18n.js` still describe the external API key as used for `/api/external/*` only.
- `README.md`, `README.en.md`, `docs/external-integration-quickstart.md`, and `docs/项目地图.md` still present legacy paths as the primary integration path.
- Legacy routes remain supported and should not be removed or hidden from compatibility notes.

## Requirements

- Use `/api/v1/external/*` as the default displayed and copied path in the Settings external API command center, starter snippets, smoke commands, and fallback endpoint maps.
- Keep legacy `/api/external/*` references only where they clearly describe backwards-compatible aliases or tests intentionally verify legacy compatibility.
- Update README and external integration quickstart examples so new clients start from `/api/v1/external/*` and learn that `/api/external/*` remains a legacy alias.
- Update Settings UI placeholder/help/i18n copy to state that `X-API-Key` applies to v1 external routes and legacy aliases.
- Mark the API versioning item in `docs/项目地图.md` as completed with a concise note that legacy compatibility remains.
- Do not change backend route behavior, auth headers, provider names, env keys, settings keys, or API-key semantics.
- Do not perform a broad visual redesign in this task; keep UI changes to externally visible copy and generated examples.

## Acceptance Criteria

- [ ] Settings external API command center fallback endpoint maps and copied snippets default to `/api/v1/external/*`.
- [ ] Settings smoke-check UI displays v1 endpoints while still allowing backend-discovered compatibility metadata to describe legacy aliases.
- [ ] README and quickstart docs use `/api/v1/external/*` for primary examples and mention `/api/external/*` only as legacy compatibility.
- [ ] Tests covering the Settings external API panel are updated to assert canonical v1 paths and legacy compatibility wording where relevant.
- [ ] Existing backend external API v1/legacy compatibility tests remain green.
- [ ] Frontend contract tests remain free of production `console.log(` / `console.debug(` additions.

## Notes

- UI brief: audience is developers/operators integrating external services; primary workflow is copying reliable starter commands; product archetype is dense operational SaaS; source of truth is backend discovery plus existing Settings command center patterns; acceptance is contract tests plus focused grep for primary legacy fallbacks.
