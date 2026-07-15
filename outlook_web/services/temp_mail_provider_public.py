from __future__ import annotations

import hashlib
import json
import secrets
import string
from datetime import datetime
from typing import Any
from urllib.parse import quote

import requests

from outlook_web.repositories import settings as settings_repo
from outlook_web.services.temp_mail_provider_base import TempMailProviderBase, register_provider
from outlook_web.services.temp_mail_provider_custom import TempMailProviderReadError

_REQUEST_TIMEOUT = 30


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def _error_code_by_status(status_code: int) -> str:
    if status_code in (401, 403):
        return "UNAUTHORIZED"
    if status_code == 404:
        return "TEMP_EMAIL_NOT_FOUND"
    if status_code == 409:
        return "TEMP_EMAIL_ALREADY_EXISTS"
    if status_code == 422:
        return "UPSTREAM_BAD_PAYLOAD"
    if status_code == 429:
        return "UPSTREAM_RATE_LIMITED"
    if status_code >= 500:
        return "UPSTREAM_SERVER_ERROR"
    return "UPSTREAM_BAD_PAYLOAD"


def _random_local_part(length: int = 10) -> str:
    alphabet = string.ascii_lowercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _random_password(length: int = 24) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _normalize_timestamp(raw_value: Any) -> int:
    if raw_value is None:
        return 0
    if isinstance(raw_value, (int, float)):
        value = int(raw_value)
        return value // 1000 if value > 1_000_000_000_000 else value

    text = str(raw_value).strip()
    if not text:
        return 0

    try:
        value = int(float(text))
        return value // 1000 if value > 1_000_000_000_000 else value
    except ValueError:
        pass

    try:
        clean = text.replace("Z", "+00:00")
        if "." in clean and "+" in clean:
            clean = clean[: clean.index(".")] + clean[clean.index("+") :]
        return int(datetime.fromisoformat(clean).timestamp())
    except (TypeError, ValueError):
        return 0


def _extract_error_message(resp: requests.Response) -> str:
    try:
        payload = resp.json()
    except Exception:
        payload = None
    if isinstance(payload, dict):
        for key in ("message", "error", "detail", "hydra:description", "hydra:title"):
            value = str(payload.get(key) or "").strip()
            if value:
                return value
    return str(resp.text or "").strip() or f"HTTP {resp.status_code}"


def _extract_hydra_items(payload: Any) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    for key in ("hydra:member", "member", "items", "data", "results", "messages", "emails"):
        value = payload.get(key)
        if isinstance(value, list):
            return value
    return []


def _extract_meta(mailbox: dict[str, Any] | str) -> dict[str, Any]:
    if not isinstance(mailbox, dict):
        return {}
    meta = mailbox.get("meta") or {}
    if isinstance(meta, str):
        try:
            parsed = json.loads(meta)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return meta if isinstance(meta, dict) else {}


def _coerce_email(mailbox: dict[str, Any] | str) -> str:
    if isinstance(mailbox, dict):
        return str(mailbox.get("email") or "").strip()
    return str(mailbox or "").strip()


def _from_address(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("address") or value.get("email") or value.get("name") or "").strip()
    return str(value or "").strip()


def _html_to_text_fallback(html_content: str) -> str:
    return str(html_content or "")


def _content_to_html(value: Any) -> str:
    if isinstance(value, list):
        return "\n".join(str(item or "") for item in value)
    return str(value or "")


class _PublicTempMailProviderMixin:
    provider_name: str

    def _read_error(self, code: str, message: str, *, operation: str, mailbox: dict[str, Any] | str, message_id: str | None = None) -> TempMailProviderReadError:
        return TempMailProviderReadError(
            code,
            message,
            data={
                "provider_name": self.provider_name,
                "operation": operation,
                "email": _coerce_email(mailbox),
                "message_id": message_id,
            },
        )


@register_provider
class MailTmTempMailProvider(_PublicTempMailProviderMixin, TempMailProviderBase):
    provider_name = "mail_tm"
    provider_label = "Mail.tm"
    provider_version = "1.0.0"
    provider_author = "OutlookMail Plus"
    provider_capabilities = {"delete_mailbox": True, "delete_message": True, "clear_messages": True}

    _base_url = "https://api.mail.tm"

    def __init__(self, *, provider_name: str | None = None):
        self.provider_name = provider_name or "mail_tm"
        self._base_url = settings_repo.get_mailtm_api_base()
        self.provider_label = "Mail.tm"

    def _service_bearer_token(self) -> str:
        return ""

    def _headers(self, token: str | None = None) -> dict[str, str]:
        headers = {"Accept": "application/ld+json, application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        elif self._service_bearer_token():
            headers["Authorization"] = f"Bearer {self._service_bearer_token()}"
        return headers

    def _json_headers(self, token: str | None = None) -> dict[str, str]:
        headers = self._headers(token)
        headers["Content-Type"] = "application/json"
        return headers

    def _fetch_domains(self) -> list[dict[str, Any]]:
        resp = requests.get(f"{self._base_url}/domains", headers=self._headers(), timeout=_REQUEST_TIMEOUT)
        if not resp.ok:
            raise RuntimeError(_extract_error_message(resp))
        items = _extract_hydra_items(resp.json())
        domains: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in items:
            if isinstance(item, dict):
                name = str(item.get("domain") or item.get("name") or "").strip()
                enabled = bool(item.get("isActive", item.get("enabled", True))) and not bool(item.get("isPrivate", False))
            else:
                name = str(item or "").strip()
                enabled = True
            if not name or name in seen:
                continue
            seen.add(name)
            domains.append({"name": name, "enabled": enabled, "is_default": False})
        for item in domains:
            if item["enabled"]:
                item["is_default"] = True
                break
        return domains

    def _resolve_domain(self, requested_domain: str | None = None) -> str:
        domain = str(requested_domain or "").strip()
        if domain:
            return domain
        domains = self._fetch_domains()
        for item in domains:
            if item.get("is_default") and item.get("enabled"):
                return str(item.get("name") or "").strip()
        for item in domains:
            if item.get("enabled"):
                return str(item.get("name") or "").strip()
        return ""

    def _login(self, address: str, password: str) -> tuple[str, str]:
        resp = requests.post(
            f"{self._base_url}/token",
            headers=self._json_headers(),
            json={"address": address, "password": password},
            timeout=_REQUEST_TIMEOUT,
        )
        if not resp.ok:
            raise RuntimeError(_extract_error_message(resp))
        payload = resp.json()
        if not isinstance(payload, dict):
            raise RuntimeError("Mail.tm token returned invalid payload")
        token = str(payload.get("token") or "").strip()
        token_id = str(payload.get("id") or "").strip()
        if not token:
            raise RuntimeError("Mail.tm token response missing token")
        return token, token_id

    def _resolve_token(self, mailbox: dict[str, Any] | str) -> str:
        meta = _extract_meta(mailbox)
        token = str(meta.get("provider_jwt") or "").strip()
        if token:
            return token
        address = _coerce_email(mailbox)
        password = str(meta.get("provider_secret") or "").strip()
        if not address or not password:
            return ""
        token, _ = self._login(address, password)
        return token

    def _refresh_token(self, mailbox: dict[str, Any] | str) -> str:
        meta = _extract_meta(mailbox)
        address = _coerce_email(mailbox)
        password = str(meta.get("provider_secret") or "").strip()
        if not address or not password:
            return ""
        token, _ = self._login(address, password)
        return token

    def _request_with_auth_retry(self, method: str, path: str, mailbox: dict[str, Any] | str, **kwargs: Any) -> requests.Response | None:
        token = self._resolve_token(mailbox)
        if not token:
            return None
        request_func = getattr(requests, method.lower())
        resp = request_func(
            f"{self._base_url}{path}",
            headers=self._headers(token),
            timeout=_REQUEST_TIMEOUT,
            **kwargs,
        )
        if resp.status_code not in (401, 403):
            return resp
        refreshed = self._refresh_token(mailbox)
        if not refreshed or refreshed == token:
            return resp
        return request_func(
            f"{self._base_url}{path}",
            headers=self._headers(refreshed),
            timeout=_REQUEST_TIMEOUT,
            **kwargs,
        )

    def _to_raw_message_id(self, message_id: str) -> str:
        text = str(message_id or "").strip()
        return text[8:] if text.startswith("mail_tm_") else text

    def _normalize_message(self, message: dict[str, Any]) -> dict[str, Any] | None:
        raw_id = str(message.get("id") or "").strip()
        if not raw_id:
            return None
        normalized_id = f"mail_tm_{raw_id}"
        html_value = message.get("html") or message.get("html_content") or ""
        if isinstance(html_value, list):
            html_content = "\n".join(str(item or "") for item in html_value)
        else:
            html_content = str(html_value or "")
        text_value = message.get("text") or message.get("content") or message.get("intro") or ""
        content = str(text_value or "") or _html_to_text_fallback(html_content)
        from_value = message.get("from") or message.get("from_address") or message.get("sender")
        timestamp = _normalize_timestamp(message.get("createdAt") or message.get("created_at") or message.get("updatedAt"))

        return {
            "id": normalized_id,
            "message_id": normalized_id,
            "from_address": _from_address(from_value),
            "subject": str(message.get("subject") or ""),
            "content": content,
            "html_content": html_content,
            "has_html": bool(html_content),
            "timestamp": timestamp,
            "created_at": str(message.get("createdAt") or message.get("created_at") or ""),
            "raw_content": json.dumps(message, ensure_ascii=False, separators=(",", ":")),
        }

    def get_options(self) -> dict[str, Any]:
        try:
            domains = self._fetch_domains()
        except Exception:
            domains = []
        return {
            "domain_strategy": "auto_or_manual",
            "default_mode": "auto",
            "domains": domains,
            "prefix_rules": {
                "min_length": 1,
                "max_length": 64,
                "pattern": r"^[a-z0-9][a-z0-9._-]*$",
            },
            "provider": self.provider_name,
            "provider_name": self.provider_name,
            "provider_label": self.provider_label,
            "api_base_url": self._base_url,
        }

    def health_check(self) -> dict[str, Any]:
        domains = self._fetch_domains()
        enabled_count = len([item for item in domains if item.get("enabled")])
        return {
            "success": enabled_count > 0,
            "method": "domains",
            "details": {
                "domain_count": len(domains),
                "enabled_domain_count": enabled_count,
                "api_base_url": self._base_url,
            },
        }

    def create_mailbox(self, *, prefix: str | None = None, domain: str | None = None) -> dict[str, Any]:
        try:
            target_domain = self._resolve_domain(domain)
        except requests.Timeout:
            return {"success": False, "error": "Mail.tm domain request timed out", "error_code": "UPSTREAM_TIMEOUT"}
        except requests.RequestException as exc:
            return {"success": False, "error": f"Mail.tm domain request failed: {exc}", "error_code": "UPSTREAM_SERVER_ERROR"}
        except Exception as exc:
            return {"success": False, "error": f"Mail.tm domain request failed: {exc}", "error_code": "UPSTREAM_BAD_PAYLOAD"}

        if not target_domain:
            return {"success": False, "error": "Mail.tm returned no available domain", "error_code": "TEMP_MAIL_PROVIDER_NOT_CONFIGURED"}

        local_part = str(prefix or "").strip() or _random_local_part()
        address = f"{local_part}@{target_domain}"
        password = _random_password()
        payload = {"address": address, "password": password}

        try:
            resp = requests.post(
                f"{self._base_url}/accounts",
                headers=self._json_headers(),
                json=payload,
                timeout=_REQUEST_TIMEOUT,
            )
        except requests.Timeout:
            return {"success": False, "error": "Mail.tm create account timed out", "error_code": "UPSTREAM_TIMEOUT"}
        except requests.RequestException as exc:
            return {"success": False, "error": f"Mail.tm create account failed: {exc}", "error_code": "UPSTREAM_SERVER_ERROR"}

        if not resp.ok:
            return {"success": False, "error": _extract_error_message(resp), "error_code": _error_code_by_status(resp.status_code)}

        try:
            account_payload = resp.json()
        except Exception:
            return {"success": False, "error": "Mail.tm account response is not JSON", "error_code": "UPSTREAM_BAD_PAYLOAD"}
        if not isinstance(account_payload, dict):
            return {"success": False, "error": "Mail.tm account response has invalid shape", "error_code": "UPSTREAM_BAD_PAYLOAD"}

        account_id = str(account_payload.get("id") or "").strip()
        returned_address = str(account_payload.get("address") or address).strip()
        try:
            token, token_id = self._login(returned_address, password)
        except requests.Timeout:
            return {"success": False, "error": "Mail.tm token request timed out", "error_code": "UPSTREAM_TIMEOUT"}
        except requests.RequestException as exc:
            return {"success": False, "error": f"Mail.tm token request failed: {exc}", "error_code": "UPSTREAM_SERVER_ERROR"}
        except Exception as exc:
            return {"success": False, "error": f"Mail.tm token request failed: {exc}", "error_code": "UNAUTHORIZED"}

        return {
            "success": True,
            "email": returned_address,
            "provider_name": self.provider_name,
            "meta": {
                "provider_name": self.provider_name,
                "provider_mailbox_id": account_id,
                "provider_jwt": token,
                "provider_secret": password,
                "provider_cursor": token_id,
                "provider_labels": [],
                "provider_capabilities": self.get_capabilities(),
                "provider_debug": {"bridge": "mail_tm"},
            },
        }

    def delete_mailbox(self, mailbox: dict[str, Any]) -> bool:
        meta = _extract_meta(mailbox)
        account_id = str(meta.get("provider_mailbox_id") or "").strip()
        if not account_id:
            return False
        token = self._resolve_token(mailbox)
        if not token:
            return False
        try:
            resp = self._request_with_auth_retry("delete", f"/accounts/{account_id}", mailbox)
            if resp is None:
                return False
            return resp.ok or resp.status_code == 404
        except requests.RequestException:
            return False

    def list_messages(self, mailbox: dict[str, Any]) -> list[dict[str, Any]] | None:
        token = self._resolve_token(mailbox)
        if not token:
            raise self._read_error("UNAUTHORIZED", "Mail.tm mailbox token is missing", operation="list_messages", mailbox=mailbox)
        try:
            resp = self._request_with_auth_retry("get", "/messages", mailbox)
        except requests.Timeout as exc:
            raise self._read_error("UPSTREAM_TIMEOUT", "Mail.tm list messages timed out", operation="list_messages", mailbox=mailbox) from exc
        except requests.RequestException as exc:
            raise self._read_error("UPSTREAM_SERVER_ERROR", f"Mail.tm list messages failed: {exc}", operation="list_messages", mailbox=mailbox) from exc

        if resp is None:
            raise self._read_error("UNAUTHORIZED", "Mail.tm mailbox token is missing", operation="list_messages", mailbox=mailbox)
        if not resp.ok:
            raise self._read_error(_error_code_by_status(resp.status_code), _extract_error_message(resp), operation="list_messages", mailbox=mailbox)
        try:
            payload = resp.json()
        except Exception as exc:
            raise self._read_error("UPSTREAM_BAD_PAYLOAD", "Mail.tm messages response is not JSON", operation="list_messages", mailbox=mailbox) from exc

        messages: list[dict[str, Any]] = []
        for item in _extract_hydra_items(payload):
            if isinstance(item, dict):
                normalized = self._normalize_message(item)
                if normalized is not None:
                    messages.append(normalized)
        return messages

    def get_message_detail(self, mailbox: dict[str, Any], message_id: str) -> dict[str, Any] | None:
        token = self._resolve_token(mailbox)
        if not token:
            raise self._read_error("UNAUTHORIZED", "Mail.tm mailbox token is missing", operation="get_message_detail", mailbox=mailbox, message_id=message_id)
        raw_id = self._to_raw_message_id(message_id)
        if not raw_id:
            return None
        try:
            resp = self._request_with_auth_retry("get", f"/messages/{raw_id}", mailbox)
        except requests.Timeout as exc:
            raise self._read_error("UPSTREAM_TIMEOUT", "Mail.tm message detail timed out", operation="get_message_detail", mailbox=mailbox, message_id=message_id) from exc
        except requests.RequestException as exc:
            raise self._read_error("UPSTREAM_SERVER_ERROR", f"Mail.tm message detail failed: {exc}", operation="get_message_detail", mailbox=mailbox, message_id=message_id) from exc
        if resp is None:
            raise self._read_error("UNAUTHORIZED", "Mail.tm mailbox token is missing", operation="get_message_detail", mailbox=mailbox, message_id=message_id)
        if resp.status_code == 404:
            return None
        if not resp.ok:
            raise self._read_error(_error_code_by_status(resp.status_code), _extract_error_message(resp), operation="get_message_detail", mailbox=mailbox, message_id=message_id)
        try:
            payload = resp.json()
        except Exception as exc:
            raise self._read_error("UPSTREAM_BAD_PAYLOAD", "Mail.tm message detail response is not JSON", operation="get_message_detail", mailbox=mailbox, message_id=message_id) from exc
        if not isinstance(payload, dict):
            return None
        return self._normalize_message(payload)

    def delete_message(self, mailbox: dict[str, Any], message_id: str) -> bool:
        token = self._resolve_token(mailbox)
        raw_id = self._to_raw_message_id(message_id)
        if not token or not raw_id:
            return False
        try:
            resp = self._request_with_auth_retry("delete", f"/messages/{raw_id}", mailbox)
            if resp is None:
                return False
            return resp.ok or resp.status_code == 404
        except requests.RequestException:
            return False

    def clear_messages(self, mailbox: dict[str, Any]) -> bool:
        messages = self.list_messages(mailbox) or []
        for item in messages:
            message_id = str(item.get("message_id") or item.get("id") or "").strip()
            if message_id and not self.delete_message(mailbox, message_id):
                return False
        return True


@register_provider
class DuckMailTempMailProvider(MailTmTempMailProvider):
    provider_name = "duckmail"
    provider_label = "DuckMail"
    provider_version = "1.0.0"
    provider_author = "OutlookMail Plus"

    def __init__(self, *, provider_name: str | None = None):
        self.provider_name = provider_name or "duckmail"
        self.provider_label = "DuckMail"
        self._base_url = settings_repo.get_duckmail_api_base()

    def _service_bearer_token(self) -> str:
        return settings_repo.get_duckmail_bearer_token()

    def _to_raw_message_id(self, message_id: str) -> str:
        text = str(message_id or "").strip()
        return text[9:] if text.startswith("duckmail_") else text

    def _normalize_message(self, message: dict[str, Any]) -> dict[str, Any] | None:
        normalized = super()._normalize_message(message)
        if normalized is None:
            return None
        for key in ("id", "message_id"):
            value = str(normalized.get(key) or "")
            normalized[key] = "duckmail_" + (value[8:] if value.startswith("mail_tm_") else value)
        return normalized

    def get_options(self) -> dict[str, Any]:
        if not self._service_bearer_token():
            return {
                "domain_strategy": "auto_or_manual",
                "default_mode": "auto",
                "domains": [],
                "prefix_rules": {
                    "min_length": 1,
                    "max_length": 64,
                    "pattern": r"^[a-z0-9][a-z0-9._-]*$",
                },
                "provider": self.provider_name,
                "provider_name": self.provider_name,
                "provider_label": self.provider_label,
                "api_base_url": self._base_url,
                "requires_bearer_token": True,
                "configured": False,
                "missing_config": ["duckmail_bearer_token"],
            }

        options = super().get_options()
        options["provider"] = self.provider_name
        options["provider_name"] = self.provider_name
        options["provider_label"] = self.provider_label
        options["api_base_url"] = self._base_url
        options["requires_bearer_token"] = True
        options["configured"] = bool(self._service_bearer_token())
        options["missing_config"] = []
        return options

    def health_check(self) -> dict[str, Any]:
        if not self._service_bearer_token():
            return {
                "success": False,
                "method": "local_config",
                "error_code": "TEMP_MAIL_PROVIDER_NOT_CONFIGURED",
                "error": "DuckMail Bearer Token is not configured",
                "details": {"missing_config": ["duckmail_bearer_token"], "api_base_url": self._base_url},
            }
        result = super().health_check()
        result["provider_name"] = self.provider_name
        return result

    def create_mailbox(self, *, prefix: str | None = None, domain: str | None = None) -> dict[str, Any]:
        if not self._service_bearer_token():
            return {"success": False, "error": "请先配置 DuckMail Bearer Token", "error_code": "TEMP_MAIL_PROVIDER_NOT_CONFIGURED"}
        result = super().create_mailbox(prefix=prefix, domain=domain)
        if result.get("success"):
            result["provider_name"] = self.provider_name
            meta = result.get("meta") if isinstance(result.get("meta"), dict) else {}
            meta["provider_name"] = self.provider_name
            meta["provider_debug"] = {"bridge": "duckmail_mail_tm"}
            result["meta"] = meta
        return result


@register_provider
class TempMailLolProvider(_PublicTempMailProviderMixin, TempMailProviderBase):
    provider_name = "tempmail_lol"
    provider_label = "TempMail.lol"
    provider_version = "1.0.0"
    provider_author = "OutlookMail Plus"
    provider_capabilities = {"delete_mailbox": False, "delete_message": False, "clear_messages": False}

    _base_url = "https://api.tempmail.lol/v2"

    def __init__(self, *, provider_name: str | None = None):
        self.provider_name = provider_name or "tempmail_lol"
        self._api_key = settings_repo.get_tempmail_lol_api_key()

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json", "User-Agent": "OutlookMailPlusTempMailProvider/1.0"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    def _extract_token(self, mailbox: dict[str, Any] | str) -> str:
        meta = _extract_meta(mailbox)
        return str(meta.get("provider_jwt") or meta.get("provider_secret") or meta.get("token") or "").strip()

    def _normalize_message(self, message: dict[str, Any], index: int = 0) -> dict[str, Any] | None:
        explicit_id = str(message.get("id") or message.get("message_id") or "").strip()
        if explicit_id:
            raw_id = explicit_id
        else:
            fingerprint = "|".join(
                [
                    str(message.get("from") or ""),
                    str(message.get("to") or ""),
                    str(message.get("subject") or ""),
                    str(message.get("date") or ""),
                    str(message.get("body") or ""),
                    str(message.get("html") or ""),
                    str(index),
                ]
            )
            raw_id = hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()[:24]

        normalized_id = f"tempmail_lol_{raw_id}"
        html_content = str(message.get("html") or message.get("html_content") or "")
        content = str(message.get("body") or message.get("text") or message.get("content") or "") or _html_to_text_fallback(html_content)
        timestamp = _normalize_timestamp(message.get("date") or message.get("timestamp") or message.get("created_at"))
        return {
            "id": normalized_id,
            "message_id": normalized_id,
            "from_address": _from_address(message.get("from") or message.get("from_address") or message.get("sender")),
            "subject": str(message.get("subject") or ""),
            "content": content,
            "html_content": html_content,
            "has_html": bool(html_content),
            "timestamp": timestamp,
            "created_at": str(message.get("date") or message.get("created_at") or ""),
            "raw_content": json.dumps(message, ensure_ascii=False, separators=(",", ":")),
        }

    def get_options(self) -> dict[str, Any]:
        return {
            "domain_strategy": "auto_or_manual",
            "default_mode": "auto",
            "domains": [],
            "prefix_rules": {
                "min_length": 1,
                "max_length": 64,
                "pattern": r"^[a-z0-9][a-z0-9._-]*$",
            },
            "provider": self.provider_name,
            "provider_name": self.provider_name,
            "provider_label": self.provider_label,
            "api_base_url": self._base_url,
        }

    def create_mailbox(self, *, prefix: str | None = None, domain: str | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if str(prefix or "").strip():
            payload["prefix"] = str(prefix or "").strip()
        if str(domain or "").strip():
            payload["domain"] = str(domain or "").strip()
        try:
            resp = requests.post(f"{self._base_url}/inbox/create", headers=self._headers(), json=payload, timeout=_REQUEST_TIMEOUT)
        except requests.Timeout:
            return {"success": False, "error": "TempMail.lol create inbox timed out", "error_code": "UPSTREAM_TIMEOUT"}
        except requests.RequestException as exc:
            return {"success": False, "error": f"TempMail.lol create inbox failed: {exc}", "error_code": "UPSTREAM_SERVER_ERROR"}

        if not resp.ok:
            return {"success": False, "error": _extract_error_message(resp), "error_code": _error_code_by_status(resp.status_code)}
        try:
            data = resp.json()
        except Exception:
            return {"success": False, "error": "TempMail.lol create response is not JSON", "error_code": "UPSTREAM_BAD_PAYLOAD"}
        if not isinstance(data, dict):
            return {"success": False, "error": "TempMail.lol create response has invalid shape", "error_code": "UPSTREAM_BAD_PAYLOAD"}
        address = str(data.get("address") or data.get("email") or "").strip()
        token = str(data.get("token") or "").strip()
        if not address or not token:
            return {"success": False, "error": "TempMail.lol response missing address or token", "error_code": "UPSTREAM_BAD_PAYLOAD"}
        return {
            "success": True,
            "email": address,
            "provider_name": self.provider_name,
            "meta": {
                "provider_name": self.provider_name,
                "provider_mailbox_id": token[:16],
                "provider_jwt": token,
                "provider_secret": token,
                "provider_cursor": "",
                "provider_labels": [],
                "provider_capabilities": self.get_capabilities(),
                "provider_debug": {"bridge": "tempmail_lol"},
            },
        }

    def delete_mailbox(self, mailbox: dict[str, Any]) -> bool:
        return True

    def list_messages(self, mailbox: dict[str, Any]) -> list[dict[str, Any]] | None:
        token = self._extract_token(mailbox)
        if not token:
            raise self._read_error("UNAUTHORIZED", "TempMail.lol inbox token is missing", operation="list_messages", mailbox=mailbox)
        try:
            resp = requests.get(f"{self._base_url}/inbox", headers=self._headers(), params={"token": token}, timeout=_REQUEST_TIMEOUT)
        except requests.Timeout as exc:
            raise self._read_error("UPSTREAM_TIMEOUT", "TempMail.lol list messages timed out", operation="list_messages", mailbox=mailbox) from exc
        except requests.RequestException as exc:
            raise self._read_error("UPSTREAM_SERVER_ERROR", f"TempMail.lol list messages failed: {exc}", operation="list_messages", mailbox=mailbox) from exc
        if not resp.ok:
            raise self._read_error(_error_code_by_status(resp.status_code), _extract_error_message(resp), operation="list_messages", mailbox=mailbox)
        try:
            payload = resp.json()
        except Exception as exc:
            raise self._read_error("UPSTREAM_BAD_PAYLOAD", "TempMail.lol inbox response is not JSON", operation="list_messages", mailbox=mailbox) from exc
        if not isinstance(payload, dict):
            raise self._read_error("UPSTREAM_BAD_PAYLOAD", "TempMail.lol inbox response has invalid shape", operation="list_messages", mailbox=mailbox)
        raw_messages = payload.get("emails") or payload.get("messages") or []
        if not isinstance(raw_messages, list):
            raise self._read_error("UPSTREAM_BAD_PAYLOAD", "TempMail.lol emails field is not a list", operation="list_messages", mailbox=mailbox)
        messages: list[dict[str, Any]] = []
        for index, item in enumerate(raw_messages):
            if isinstance(item, dict):
                normalized = self._normalize_message(item, index=index)
                if normalized is not None:
                    messages.append(normalized)
        return messages

    def get_message_detail(self, mailbox: dict[str, Any], message_id: str) -> dict[str, Any] | None:
        messages = self.list_messages(mailbox) or []
        for item in messages:
            if item.get("id") == message_id or item.get("message_id") == message_id:
                return item
        return None

    def delete_message(self, mailbox: dict[str, Any], message_id: str) -> bool:
        return True

    def clear_messages(self, mailbox: dict[str, Any]) -> bool:
        return True


@register_provider
class EmailnatorTempMailProvider(_PublicTempMailProviderMixin, TempMailProviderBase):
    provider_name = "emailnator"
    provider_label = "Emailnator"
    provider_version = "1.0.0"
    provider_author = "OutlookMail Plus"
    provider_capabilities = {"delete_mailbox": False, "delete_message": True, "clear_messages": True}

    _base_url = "https://gmailnator.p.rapidapi.com/api"
    _valid_types = set(settings_repo.EMAILNATOR_VALID_EMAIL_TYPES)

    def __init__(self, *, provider_name: str | None = None):
        self.provider_name = provider_name or "emailnator"

    def _api_key(self) -> str:
        return settings_repo.get_emailnator_api_key()

    def _email_types(self) -> list[str]:
        return [item for item in settings_repo.get_emailnator_email_types() if item in self._valid_types]

    def _headers(self) -> dict[str, str]:
        return {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-RapidAPI-Key": self._api_key(),
            "X-RapidAPI-Host": "gmailnator.p.rapidapi.com",
        }

    def _ensure_configured(self) -> str:
        api_key = self._api_key()
        if not api_key:
            raise RuntimeError("请先配置 Emailnator RapidAPI Key")
        return api_key

    def _to_raw_message_id(self, message_id: str) -> str:
        text = str(message_id or "").strip()
        return text[11:] if text.startswith("emailnator_") else text

    def _normalize_message(self, message: dict[str, Any], *, raw_id_override: str | None = None) -> dict[str, Any] | None:
        raw_id = str(raw_id_override or message.get("id") or message.get("message_id") or "").strip()
        if not raw_id:
            return None
        normalized_id = f"emailnator_{raw_id}"
        html_content = _content_to_html(message.get("content") or message.get("html") or message.get("html_content") or "")
        text_content = str(message.get("text") or message.get("body") or "") or _html_to_text_fallback(html_content)
        timestamp = _normalize_timestamp(message.get("timestamp") or message.get("created_at") or message.get("date"))
        return {
            "id": normalized_id,
            "message_id": normalized_id,
            "from_address": _from_address(message.get("from") or message.get("from_address") or message.get("sender")),
            "subject": str(message.get("subject") or ""),
            "content": text_content,
            "html_content": html_content,
            "has_html": bool(html_content),
            "timestamp": timestamp,
            "created_at": str(message.get("time_ago") or message.get("created_at") or ""),
            "raw_content": json.dumps(message, ensure_ascii=False, separators=(",", ":")),
        }

    def get_options(self) -> dict[str, Any]:
        return {
            "domain_strategy": "auto",
            "default_mode": "auto",
            "domains": [],
            "prefix_rules": {
                "min_length": 1,
                "max_length": 64,
                "pattern": r"^[a-z0-9][a-z0-9._+-]*$",
            },
            "provider": self.provider_name,
            "provider_name": self.provider_name,
            "provider_label": self.provider_label,
            "api_base_url": self._base_url,
            "requires_api_key": True,
            "configured": bool(self._api_key()),
            "email_types": self._email_types(),
        }

    def create_mailbox(self, *, prefix: str | None = None, domain: str | None = None) -> dict[str, Any]:
        try:
            self._ensure_configured()
        except RuntimeError as exc:
            return {"success": False, "error": str(exc), "error_code": "TEMP_MAIL_PROVIDER_NOT_CONFIGURED"}

        payload: dict[str, Any] = {}
        email_types = self._email_types()
        if email_types:
            payload["type"] = email_types
        try:
            resp = requests.post(
                f"{self._base_url}/emails/generate",
                headers=self._headers(),
                json=payload if payload else None,
                timeout=_REQUEST_TIMEOUT,
            )
        except requests.Timeout:
            return {"success": False, "error": "Emailnator create email timed out", "error_code": "UPSTREAM_TIMEOUT"}
        except requests.RequestException as exc:
            return {"success": False, "error": f"Emailnator create email failed: {exc}", "error_code": "UPSTREAM_SERVER_ERROR"}

        if not resp.ok:
            return {"success": False, "error": _extract_error_message(resp), "error_code": _error_code_by_status(resp.status_code)}
        try:
            data = resp.json()
        except Exception:
            return {"success": False, "error": "Emailnator create response is not JSON", "error_code": "UPSTREAM_BAD_PAYLOAD"}
        if not isinstance(data, dict):
            return {"success": False, "error": "Emailnator create response has invalid shape", "error_code": "UPSTREAM_BAD_PAYLOAD"}
        address = str(data.get("email") or data.get("address") or "").strip()
        if not address:
            return {"success": False, "error": "Emailnator response missing email", "error_code": "UPSTREAM_BAD_PAYLOAD"}
        return {
            "success": True,
            "email": address,
            "provider_name": self.provider_name,
            "meta": {
                "provider_name": self.provider_name,
                "provider_mailbox_id": address,
                "provider_jwt": "",
                "provider_secret": "",
                "provider_cursor": str(data.get("type") or ""),
                "provider_labels": email_types,
                "provider_capabilities": self.get_capabilities(),
                "provider_debug": {"bridge": "emailnator_rapidapi"},
            },
        }

    def delete_mailbox(self, mailbox: dict[str, Any]) -> bool:
        return True

    def list_messages(self, mailbox: dict[str, Any]) -> list[dict[str, Any]] | None:
        try:
            self._ensure_configured()
        except RuntimeError as exc:
            raise self._read_error("TEMP_MAIL_PROVIDER_NOT_CONFIGURED", str(exc), operation="list_messages", mailbox=mailbox) from exc
        email_addr = _coerce_email(mailbox)
        if not email_addr:
            raise self._read_error("TEMP_EMAIL_NOT_FOUND", "Emailnator mailbox email is missing", operation="list_messages", mailbox=mailbox)
        try:
            resp = requests.post(
                f"{self._base_url}/inbox",
                headers=self._headers(),
                json={"email": email_addr, "limit": 20},
                timeout=_REQUEST_TIMEOUT,
            )
        except requests.Timeout as exc:
            raise self._read_error("UPSTREAM_TIMEOUT", "Emailnator list messages timed out", operation="list_messages", mailbox=mailbox) from exc
        except requests.RequestException as exc:
            raise self._read_error("UPSTREAM_SERVER_ERROR", f"Emailnator list messages failed: {exc}", operation="list_messages", mailbox=mailbox) from exc
        if not resp.ok:
            raise self._read_error(_error_code_by_status(resp.status_code), _extract_error_message(resp), operation="list_messages", mailbox=mailbox)
        try:
            payload = resp.json()
        except Exception as exc:
            raise self._read_error("UPSTREAM_BAD_PAYLOAD", "Emailnator inbox response is not JSON", operation="list_messages", mailbox=mailbox) from exc
        if not isinstance(payload, dict):
            raise self._read_error("UPSTREAM_BAD_PAYLOAD", "Emailnator inbox response has invalid shape", operation="list_messages", mailbox=mailbox)
        raw_messages = payload.get("messages") or []
        if not isinstance(raw_messages, list):
            raise self._read_error("UPSTREAM_BAD_PAYLOAD", "Emailnator messages field is not a list", operation="list_messages", mailbox=mailbox)
        messages: list[dict[str, Any]] = []
        for item in raw_messages:
            if isinstance(item, dict):
                normalized = self._normalize_message(item)
                if normalized is not None:
                    messages.append(normalized)
        return messages

    def get_message_detail(self, mailbox: dict[str, Any], message_id: str) -> dict[str, Any] | None:
        try:
            self._ensure_configured()
        except RuntimeError as exc:
            raise self._read_error("TEMP_MAIL_PROVIDER_NOT_CONFIGURED", str(exc), operation="get_message_detail", mailbox=mailbox, message_id=message_id) from exc
        raw_id = self._to_raw_message_id(message_id)
        if not raw_id:
            return None
        try:
            resp = requests.get(
                f"{self._base_url}/inbox/{quote(raw_id, safe='')}",
                headers=self._headers(),
                timeout=_REQUEST_TIMEOUT,
            )
        except requests.Timeout as exc:
            raise self._read_error("UPSTREAM_TIMEOUT", "Emailnator message detail timed out", operation="get_message_detail", mailbox=mailbox, message_id=message_id) from exc
        except requests.RequestException as exc:
            raise self._read_error("UPSTREAM_SERVER_ERROR", f"Emailnator message detail failed: {exc}", operation="get_message_detail", mailbox=mailbox, message_id=message_id) from exc
        if resp.status_code == 404:
            return None
        if not resp.ok:
            raise self._read_error(_error_code_by_status(resp.status_code), _extract_error_message(resp), operation="get_message_detail", mailbox=mailbox, message_id=message_id)
        try:
            payload = resp.json()
        except Exception as exc:
            raise self._read_error("UPSTREAM_BAD_PAYLOAD", "Emailnator message detail response is not JSON", operation="get_message_detail", mailbox=mailbox, message_id=message_id) from exc
        if not isinstance(payload, dict):
            return None
        return self._normalize_message(payload, raw_id_override=raw_id)

    def delete_message(self, mailbox: dict[str, Any], message_id: str) -> bool:
        if not self._api_key():
            return False
        raw_id = self._to_raw_message_id(message_id)
        if not raw_id:
            return False
        try:
            resp = requests.delete(
                f"{self._base_url}/inbox/{quote(raw_id, safe='')}",
                headers=self._headers(),
                timeout=_REQUEST_TIMEOUT,
            )
            return resp.ok or resp.status_code == 404
        except requests.RequestException:
            return False

    def clear_messages(self, mailbox: dict[str, Any]) -> bool:
        messages = self.list_messages(mailbox) or []
        for item in messages:
            message_id = str(item.get("message_id") or item.get("id") or "").strip()
            if message_id and not self.delete_message(mailbox, message_id):
                return False
        return True
