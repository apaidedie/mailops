from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass

DEFAULT_URL = "http://localhost:5000/healthz"
DEFAULT_TIMEOUT_SECONDS = 4.0


@dataclass(frozen=True)
class HealthcheckResult:
    ok: bool
    message: str


def _response_requires_json_check(content_type: str, body: bytes) -> bool:
    if "json" in content_type.lower():
        return True
    stripped = body.lstrip()
    return stripped.startswith(b"{") or stripped.startswith(b"[")


def check_health(
    url: str = DEFAULT_URL,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> HealthcheckResult:
    request = urllib.request.Request(url, headers={"Accept": "application/json"})

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status_code = response.getcode()
            content_type = response.headers.get("Content-Type", "")
            body = response.read()
    except urllib.error.HTTPError as exc:
        return HealthcheckResult(False, f"healthcheck failed: HTTP {exc.code} from {url}")
    except Exception as exc:  # pragma: no cover - exercised through CLI tests.
        return HealthcheckResult(False, f"healthcheck failed: {type(exc).__name__}: {exc}")

    if status_code != 200:
        return HealthcheckResult(False, f"healthcheck failed: HTTP {status_code} from {url}")

    if _response_requires_json_check(content_type, body):
        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            return HealthcheckResult(False, f"healthcheck failed: invalid JSON response: {exc}")

        if not isinstance(payload, dict):
            return HealthcheckResult(False, "healthcheck failed: JSON response must be an object")
        if payload.get("status") != "ok":
            return HealthcheckResult(False, "healthcheck failed: JSON status is not ok")

    return HealthcheckResult(True, f"healthcheck ok: {url}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check the Outlook Email Plus health endpoint.")
    parser.add_argument(
        "--url",
        default=DEFAULT_URL,
        help=f"Health endpoint URL. Default: {DEFAULT_URL}",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=f"Request timeout in seconds. Default: {DEFAULT_TIMEOUT_SECONDS:g}",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.timeout <= 0:
        print("healthcheck failed: --timeout must be greater than 0", file=sys.stderr)
        return 2

    result = check_health(url=args.url, timeout=args.timeout)
    stream = sys.stdout if result.ok else sys.stderr
    print(result.message, file=stream)
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
