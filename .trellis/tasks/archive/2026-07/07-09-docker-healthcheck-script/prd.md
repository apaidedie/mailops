# Docker healthcheck script

## Goal

Make container health checks easier to maintain by replacing duplicated inline
Python snippets in Docker deployment files with one repository-owned script.
The script must keep the current `/healthz` contract and stay dependency-free so
it works inside the slim production image.

## Confirmed Facts

- `Dockerfile` and `docker-compose.yml` both call an inline `urllib.request`
  one-liner against `http://localhost:5000/healthz`.
- The project already exposes `GET /healthz` as the explicit deployment health
  endpoint in README deployment notes.
- Previous deployment work keeps Gunicorn at one worker with multiple threads to
  avoid duplicating in-process scheduler work while reducing request queueing.
- Existing tests cover Gunicorn startup configuration and `/healthz` response
  contracts, but not a reusable container healthcheck script.

## Requirements

- Add a zero-dependency Python healthcheck script under `scripts/`.
- The script must default to `http://localhost:5000/healthz` and a short timeout
  suitable for Docker health checks.
- The script must return exit code `0` only when the endpoint returns HTTP 200
  and, for JSON responses, reports `status=ok`.
- The script must emit concise failure details to stderr without exposing
  secrets or environment values unrelated to the check.
- `Dockerfile` and `docker-compose.yml` must use the script instead of
  maintaining duplicate inline Python snippets.
- Tests must cover the script behavior and the Docker/Compose wiring.

## Acceptance Criteria

- [x] `python scripts/healthcheck.py --url <healthy-test-server>` exits `0`.
- [x] The script exits non-zero for non-200 responses, invalid JSON status, and
      connection failures.
- [x] `Dockerfile` healthcheck invokes `python scripts/healthcheck.py`.
- [x] `docker-compose.yml` healthcheck invokes `python scripts/healthcheck.py`.
- [x] Targeted tests for the new script and deployment wiring pass.

## Out of Scope

- Changing the runtime `/healthz` API response shape.
- Changing Gunicorn worker/thread defaults.
- Reworking provider selection, external API behavior, or UI.
