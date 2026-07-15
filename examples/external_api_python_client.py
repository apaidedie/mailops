from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


CANONICAL_EXTERNAL_PREFIX = "/api/v1/external"
DEFAULT_ENDPOINTS = {
    "capabilities": f"{CANONICAL_EXTERNAL_PREFIX}/capabilities",
    "integration_bundle": f"{CANONICAL_EXTERNAL_PREFIX}/integration-bundle",
    "providers": f"{CANONICAL_EXTERNAL_PREFIX}/providers",
    "docs": f"{CANONICAL_EXTERNAL_PREFIX}/docs",
    "openapi": f"{CANONICAL_EXTERNAL_PREFIX}/openapi.json",
    "mailbox_session_start": f"{CANONICAL_EXTERNAL_PREFIX}/mailbox-sessions/start",
    "mailbox_session_read": f"{CANONICAL_EXTERNAL_PREFIX}/mailbox-sessions/read",
    "mailbox_session_close": f"{CANONICAL_EXTERNAL_PREFIX}/mailbox-sessions/close",
}
READ_FILTER_FIELDS = {
    "email",
    "claim_token",
    "task_token",
    "message_id",
    "folder",
    "skip",
    "top",
    "from_contains",
    "subject_contains",
    "since_minutes",
    "code_length",
    "code_regex",
    "code_source",
    "timeout_seconds",
    "poll_interval",
    "mode",
}
SECRET_TARGET_PATTERNS = (
    re.compile(r"dk_[0-9a-fA-F]{20,}"),
    re.compile(r"(?i)(api[_-]?key|bearer|token|password|secret|jwt|refresh[_-]?token)\s*[:=]\s*(?!<|$)[A-Za-z0-9._~+/=-]{12,}"),
    re.compile(r"(?i)bearer\s+(?!<)[A-Za-z0-9._~+/=-]{12,}"),
)


class OutlookEmailPlusApiError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        status: int | None = None,
        code: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.payload = payload or {}


@dataclass(frozen=True)
class HttpResponse:
    status: int
    payload: dict[str, Any]


Transport = Callable[[str, str, str, dict[str, Any] | None, float], HttpResponse]


def _join_url(base_url: str, path: str) -> str:
    return urllib.parse.urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))


def _urllib_transport(method: str, url: str, api_key: str, body: dict[str, Any] | None, timeout: float) -> HttpResponse:
    headers = {"X-API-Key": api_key, "Accept": "application/json"}
    data: bytes | None = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers, method=method.upper())
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            status = int(getattr(response, "status", 200))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        payload = _parse_json_object(raw)
        raise OutlookEmailPlusApiError(
            f"{method.upper()} {url} failed with HTTP {exc.code}",
            status=exc.code,
            code=str(payload.get("code") or "HTTP_ERROR"),
            payload=payload,
        ) from exc
    except urllib.error.URLError as exc:
        raise OutlookEmailPlusApiError(f"{method.upper()} {url} failed: {exc.reason}") from exc
    payload = _parse_json_object(raw)
    return HttpResponse(status=status, payload=payload)


def _parse_json_object(raw: str) -> dict[str, Any]:
    try:
        payload = json.loads(raw or "{}")
    except json.JSONDecodeError as exc:
        raise OutlookEmailPlusApiError("response was not valid JSON") from exc
    if not isinstance(payload, dict):
        raise OutlookEmailPlusApiError("response JSON was not an object")
    return payload


def _data_or_payload(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data")
    if isinstance(data, dict):
        return data
    return payload


def _compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _workflow_summary(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    workflows = manifest.get("workflows") if isinstance(manifest.get("workflows"), list) else []
    summary: list[dict[str, Any]] = []
    for workflow in workflows:
        if not isinstance(workflow, dict):
            continue
        key = workflow.get("key")
        if not key:
            continue
        summary.append(
            _without_none(
                {
                    "key": str(key),
                    "label": str(workflow.get("label")) if workflow.get("label") else None,
                    "description": str(workflow.get("description")) if workflow.get("description") else None,
                }
            )
        )
    return summary


def summarize_integration_bundle_action_plan(bundle: dict[str, Any]) -> dict[str, Any]:
    action_plan = _as_dict(bundle.get("action_plan"))
    if not action_plan:
        return _fallback_action_plan_summary(bundle)

    items = _action_plan_item_summaries(action_plan.get("items"))
    return _action_plan_summary(
        source="action_plan",
        status=_text_value(action_plan.get("status") or bundle.get("status"), "unknown"),
        items=items,
        plan_summary=action_plan.get("summary"),
    )


def _fallback_action_plan_summary(bundle: dict[str, Any]) -> dict[str, Any]:
    status = _bundle_readiness_status(bundle)
    endpoints = _as_dict(bundle.get("endpoints"))
    ready = status == "ready"
    items: list[dict[str, Any]] = [
        {
            "key": "inspect_readiness",
            "priority": "medium" if ready else "high",
            "status": "optional" if ready else "action_required",
            "blocking": not ready,
            "title": "Inspect readiness details",
        }
    ]
    session_start = endpoints.get("mailbox_session_start")
    if ready and session_start:
        items.append(
            {
                "key": "start_mailbox_session",
                "priority": "medium",
                "status": "ready",
                "blocking": False,
                "title": "Start provider-neutral mailbox session",
                "endpoint": str(session_start),
            }
        )
    return _action_plan_summary(source="fallback_readiness", status=status, items=items, plan_summary=None)


def _action_plan_item_summaries(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    items: list[dict[str, Any]] = []
    for raw_item in value:
        item = _as_dict(raw_item)
        key = item.get("key")
        if not key:
            continue
        summary = {
            "key": str(key),
            "priority": _text_value(item.get("priority"), "medium"),
            "status": _text_value(item.get("status"), "optional"),
            "blocking": bool(item.get("blocking")),
            "title": _text_value(item.get("title"), str(key).replace("_", " ")),
        }
        redacted = False
        for target_key in ("endpoint", "command", "docs"):
            value = item.get(target_key)
            if isinstance(value, str) and value.strip():
                safe_value = _safe_action_target(value)
                if safe_value is None:
                    redacted = True
                else:
                    summary[target_key] = safe_value
        if redacted:
            summary["target_redacted"] = True
        items.append(summary)
    return items


def _action_plan_summary(
    *,
    source: str,
    status: str,
    items: list[dict[str, Any]],
    plan_summary: Any,
) -> dict[str, Any]:
    return {
        "source": source,
        "status": status,
        "summary": _action_plan_summary_counts(plan_summary, items),
        "blocking_keys": [str(item["key"]) for item in items if item.get("blocking")],
        "action_required_keys": [
            str(item["key"]) for item in items if item.get("status") in {"action_required", "blocked"}
        ],
        "ready_next_steps": [
            str(item["key"]) for item in items if item.get("status") == "ready" and not item.get("blocking")
        ],
        "items": items,
    }


def _action_plan_summary_counts(plan_summary: Any, items: list[dict[str, Any]]) -> dict[str, int]:
    computed = {
        "total": len(items),
        "blocking": sum(1 for item in items if item.get("blocking")),
        "high": sum(1 for item in items if item.get("priority") == "high"),
        "medium": sum(1 for item in items if item.get("priority") == "medium"),
        "low": sum(1 for item in items if item.get("priority") == "low"),
    }
    source = _as_dict(plan_summary)
    return {key: _non_negative_int(source.get(key), computed[key]) for key in computed}


def _non_negative_int(value: Any, fallback: int) -> int:
    if isinstance(value, bool):
        return fallback
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return fallback
    return parsed if parsed >= 0 else fallback


def _bundle_readiness_status(bundle: dict[str, Any]) -> str:
    readiness = _as_dict(bundle.get("readiness"))
    providers = _as_dict(readiness.get("providers"))
    external_api = _as_dict(readiness.get("external_api"))
    for value in (
        bundle.get("status"),
        readiness.get("status"),
        readiness.get("overall_status"),
        providers.get("overall_status"),
        providers.get("status"),
        external_api.get("status"),
    ):
        text = _text_value(value, "")
        if text:
            return text
    return "unknown"


def _text_value(value: Any, default: str) -> str:
    if isinstance(value, str) and value.strip():
        return value
    return default


def _safe_action_target(value: str) -> str | None:
    text = value.strip()
    if not text:
        return None
    if any(pattern.search(text) for pattern in SECRET_TARGET_PATTERNS):
        return None
    return value


def build_integration_bundle(base_url: str, discovery: dict[str, Any]) -> dict[str, Any]:
    capabilities = _as_dict(discovery.get("capabilities"))
    providers = _as_dict(discovery.get("providers"))
    openapi = _as_dict(discovery.get("openapi"))
    manifest = _as_dict(capabilities.get("integration_manifest"))
    deployment_profile = _as_dict(capabilities.get("deployment_profile") or manifest.get("deployment"))
    selection_policy = _as_dict(capabilities.get("selection_policy") or manifest.get("selection"))
    provider_readiness = _as_dict(providers.get("readiness_summary"))
    auth = _as_dict(manifest.get("auth") or capabilities.get("auth"))
    return {
        "base_url": base_url.rstrip("/"),
        "endpoints": discovery.get("endpoints") or capabilities.get("endpoints") or {},
        "auth": {
            "header": str(auth.get("header") or "X-API-Key"),
            "placeholder": str(auth.get("placeholder") or "<your-api-key>"),
        },
        "documentation": _as_dict(capabilities.get("documentation") or manifest.get("documentation")),
        "provider_selection": {
            "source_priority": selection_policy.get("source_priority")
            or deployment_profile.get("priority")
            or deployment_profile.get("source_priority")
            or [],
            "provider_values": deployment_profile.get("provider_values") or selection_policy.get("provider_values") or {},
            "config_file": selection_policy.get("config_file") or deployment_profile.get("config_file") or {},
        },
        "templates": deployment_profile.get("templates") or selection_policy.get("templates") or {},
        "workflows": _workflow_summary(manifest),
        "readiness": {
            "overall_status": provider_readiness.get("overall_status"),
            "totals": provider_readiness.get("totals") or {},
            "issues": provider_readiness.get("issues") or {},
        },
        "openapi": {
            "version": str(openapi.get("openapi") or ""),
            "path_count": len(openapi.get("paths") or {}) if isinstance(openapi.get("paths"), dict) else 0,
        },
    }


def _should_fallback_to_local_bundle(exc: OutlookEmailPlusApiError) -> bool:
    return exc.status in {404, 405, 501} or exc.code in {"NOT_FOUND", "METHOD_NOT_ALLOWED", "NOT_IMPLEMENTED"}


class OutlookEmailPlusClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        timeout: float = 20.0,
        transport: Transport | None = None,
    ) -> None:
        if not base_url.strip():
            raise ValueError("base_url is required")
        if not api_key.strip():
            raise ValueError("api_key is required")
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self._transport = transport or _urllib_transport
        self._endpoints = dict(DEFAULT_ENDPOINTS)

    @property
    def endpoints(self) -> dict[str, str]:
        return dict(self._endpoints)

    def discover(self) -> dict[str, Any]:
        capabilities = self.get("capabilities")
        capability_data = _data_or_payload(capabilities)
        endpoints = capability_data.get("endpoints")
        if isinstance(endpoints, dict):
            self._endpoints.update({str(key): str(value) for key, value in endpoints.items() if value})
        providers = self.get("providers")
        openapi = self.get("openapi")
        documentation = capability_data.get("documentation") if isinstance(capability_data.get("documentation"), dict) else {}
        return {
            "capabilities": capability_data,
            "providers": _data_or_payload(providers),
            "openapi": openapi,
            "documentation": documentation,
            "endpoints": self.endpoints,
        }

    def integration_bundle(self) -> dict[str, Any]:
        try:
            return _data_or_payload(self.get("integration_bundle"))
        except ValueError:
            return build_integration_bundle(self.base_url, self.discover())
        except OutlookEmailPlusApiError as exc:
            if not _should_fallback_to_local_bundle(exc):
                raise
            return build_integration_bundle(self.base_url, self.discover())

    def get(self, endpoint_key: str) -> dict[str, Any]:
        return self._request("GET", self._endpoint(endpoint_key), None)

    def post(self, endpoint_key: str, body: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", self._endpoint(endpoint_key), body)

    def start_mailbox_session(
        self,
        *,
        caller_id: str,
        task_id: str,
        source_strategy: str = "pool_first",
        provider: str | None = None,
        provider_name: str | None = None,
        email_domain: str | None = None,
        project_key: str | None = None,
        prefix: str | None = None,
        domain: str | None = None,
    ) -> dict[str, Any]:
        body = _without_none(
            {
                "caller_id": caller_id,
                "task_id": task_id,
                "source_strategy": source_strategy,
                "provider": provider,
                "provider_name": provider_name,
                "email_domain": email_domain,
                "project_key": project_key,
                "prefix": prefix,
                "domain": domain,
            }
        )
        return _data_or_payload(self.post("mailbox_session_start", body))

    def read_session(
        self,
        *,
        session_type: str,
        read_action: str,
        caller_id: str,
        task_id: str,
        **filters: Any,
    ) -> dict[str, Any]:
        body = {
            "session_type": session_type,
            "read_action": read_action,
            "caller_id": caller_id,
            "task_id": task_id,
        }
        for key, value in filters.items():
            if key not in READ_FILTER_FIELDS:
                raise ValueError(f"unsupported read filter: {key}")
            body[key] = value
        return _data_or_payload(self.post("mailbox_session_read", _without_none(body)))

    def read_verification_code(self, *, session_type: str, caller_id: str, task_id: str, **filters: Any) -> dict[str, Any]:
        return self.read_session(
            session_type=session_type,
            read_action="verification_code",
            caller_id=caller_id,
            task_id=task_id,
            **filters,
        )

    def close_session(
        self,
        *,
        session_type: str,
        caller_id: str,
        task_id: str,
        account_id: int | None = None,
        claim_token: str | None = None,
        task_token: str | None = None,
        result: str | None = "success",
        detail: str | None = None,
        reason: str | None = None,
    ) -> dict[str, Any]:
        body = _without_none(
            {
                "session_type": session_type,
                "caller_id": caller_id,
                "task_id": task_id,
                "account_id": account_id,
                "claim_token": claim_token,
                "task_token": task_token,
                "result": result,
                "detail": detail,
                "reason": reason,
            }
        )
        return _data_or_payload(self.post("mailbox_session_close", body))

    def verification_flow(
        self,
        *,
        caller_id: str,
        task_id: str,
        source_strategy: str = "pool_first",
        provider: str | None = None,
        provider_name: str | None = None,
        email_domain: str | None = None,
        project_key: str | None = None,
        prefix: str | None = None,
        domain: str | None = None,
        since_minutes: int = 10,
        close_result: str = "success",
    ) -> dict[str, Any]:
        session: dict[str, Any] | None = None
        close_data: dict[str, Any] | None = None
        verification: dict[str, Any] | None = None
        try:
            session = self.start_mailbox_session(
                caller_id=caller_id,
                task_id=task_id,
                source_strategy=source_strategy,
                provider=provider,
                provider_name=provider_name,
                email_domain=email_domain,
                project_key=project_key,
                prefix=prefix,
                domain=domain,
            )
            verification = self.read_verification_code(
                session_type=str(session.get("session_type") or ""),
                caller_id=caller_id,
                task_id=task_id,
                email=session.get("email"),
                claim_token=_lifecycle_value(session, "claim_token"),
                task_token=_lifecycle_value(session, "task_token"),
                since_minutes=since_minutes,
            )
        finally:
            if session:
                close_data = self.close_session(
                    session_type=str(session.get("session_type") or ""),
                    caller_id=caller_id,
                    task_id=task_id,
                    account_id=_lifecycle_value(session, "account_id"),
                    claim_token=_lifecycle_value(session, "claim_token"),
                    task_token=_lifecycle_value(session, "task_token"),
                    result=close_result,
                )
        return {"session": session, "verification": verification, "close": close_data}

    def _endpoint(self, key: str) -> str:
        endpoint = self._endpoints.get(key)
        if not endpoint:
            raise ValueError(f"unknown endpoint key: {key}")
        return endpoint

    def _request(self, method: str, path: str, body: dict[str, Any] | None) -> dict[str, Any]:
        url = _join_url(self.base_url, path)
        response = self._transport(method.upper(), url, self.api_key, body, self.timeout)
        payload = response.payload
        if payload.get("success") is False:
            code = str(payload.get("code") or "API_ERROR")
            message = str(payload.get("message") or code)
            raise OutlookEmailPlusApiError(message, status=response.status, code=code, payload=payload)
        return payload


def _without_none(values: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in values.items() if value is not None}


def _lifecycle_value(session: dict[str, Any], key: str) -> Any:
    lifecycle = session.get("lifecycle") if isinstance(session.get("lifecycle"), dict) else {}
    if key in lifecycle:
        return lifecycle.get(key)
    return session.get(key)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Outlook Email Plus external API starter client")
    parser.add_argument("--base-url", required=True, help="Outlook Email Plus instance base URL")
    parser.add_argument(
        "--api-key",
        default=os.environ.get("OUTLOOK_EMAIL_PLUS_API_KEY", ""),
        help="External API key. Defaults to OUTLOOK_EMAIL_PLUS_API_KEY.",
    )
    parser.add_argument("--timeout", type=float, default=20.0, help="HTTP timeout in seconds")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("discover", help="Read-only discovery: capabilities, providers, OpenAPI metadata")
    bundle = subparsers.add_parser(
        "integration-bundle",
        help="Read-only discovery bundle for external service deployment planning",
    )
    bundle.add_argument("--output", help="Optional JSON file path. Defaults to stdout.")
    bundle.add_argument(
        "--summary",
        action="store_true",
        help="Print only a concise action-plan readiness summary instead of the full bundle.",
    )

    verification = subparsers.add_parser(
        "verification-code",
        help="Stateful demo: start a mailbox session, read a verification code, then close it",
    )
    verification.add_argument("--caller-id", required=True)
    verification.add_argument("--task-id", required=True)
    verification.add_argument("--source-strategy", default="pool_first")
    verification.add_argument("--provider")
    verification.add_argument("--provider-name")
    verification.add_argument("--email-domain")
    verification.add_argument("--project-key")
    verification.add_argument("--prefix")
    verification.add_argument("--domain")
    verification.add_argument("--since-minutes", type=int, default=10)
    verification.add_argument("--result", default="success")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if not args.api_key:
        parser.error("--api-key or OUTLOOK_EMAIL_PLUS_API_KEY is required")
    client = OutlookEmailPlusClient(args.base_url, args.api_key, timeout=args.timeout)
    try:
        if args.command == "discover":
            print(_compact_json(client.discover()))
            return 0
        if args.command == "integration-bundle":
            bundle = client.integration_bundle()
            payload = summarize_integration_bundle_action_plan(bundle) if args.summary else bundle
            serialized = _compact_json(payload)
            if args.output:
                output_path = Path(args.output)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(serialized + "\n", encoding="utf-8")
                print(str(output_path))
                return 0
            print(serialized)
            return 0
        if args.command == "verification-code":
            result = client.verification_flow(
                caller_id=args.caller_id,
                task_id=args.task_id,
                source_strategy=args.source_strategy,
                provider=args.provider,
                provider_name=args.provider_name,
                email_domain=args.email_domain,
                project_key=args.project_key,
                prefix=args.prefix,
                domain=args.domain,
                since_minutes=args.since_minutes,
                close_result=args.result,
            )
            print(_compact_json(result))
            return 0
    except OutlookEmailPlusApiError as exc:
        print(f"External API error: {exc}", file=sys.stderr)
        if exc.payload:
            print(_compact_json(exc.payload), file=sys.stderr)
        return 2
    parser.error(f"unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
