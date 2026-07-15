from __future__ import annotations

import json
from typing import Any
from urllib.parse import quote

from outlook_web.services.temp_mail_provider_base import TempMailProviderBase, register_provider


PROVIDER_KEY = "template_temp_mail"
DEFAULT_API_BASE_URL = "https://api.example.test"
DEFAULT_DOMAIN = "example.test"
REQUEST_TIMEOUT_SECONDS = 30


@register_provider
class TemplateTempMailProvider(TempMailProviderBase):
    """Copy this file to the runtime plugin directory and replace the adapters.

    Runtime plugin path:
    <DATABASE_PATH parent>/plugins/temp_mail_providers/<provider_name>.py

    This template is intentionally import-safe: it does not read upstream
    networks during import or contract validation. Provider-specific API work is
    isolated in small request and normalization helpers below.
    """

    provider_name = PROVIDER_KEY
    provider_label = "Template Temp Mail"
    provider_version = "0.1.0"
    provider_author = "OutlookMail Plus"
    provider_capabilities = {"delete_mailbox": True, "delete_message": True, "clear_messages": True}
    config_schema = {
        "fields": [
            {
                "key": "api_base_url",
                "label": "API Base URL",
                "type": "url",
                "required": True,
                "default": DEFAULT_API_BASE_URL,
            },
            {
                "key": "api_key",
                "label": "API Key",
                "type": "password",
                "required": True,
            },
        ]
    }

    def __init__(self, *, provider_name: str | None = None, config: dict[str, Any] | None = None):
        self.provider_name = provider_name or self.provider_name
        self._config = dict(config or {})

    def _config_value(self, key: str, default: str = "") -> str:
        if key in self._config:
            return str(self._config.get(key) or "").strip()

        # Plugin settings are persisted as plugin.<provider>.<field>. Keep the
        # import lazy so structural validation can run without app setup.
        try:
            from outlook_web.repositories import settings as settings_repo

            return str(settings_repo.get_setting(f"plugin.{self.provider_name}.{key}", default) or "").strip()
        except Exception:
            return str(default or "").strip()

    def _api_base_url(self) -> str:
        return self._config_value("api_base_url", DEFAULT_API_BASE_URL).rstrip("/")

    def _api_key(self) -> str:
        return self._config_value("api_key")

    def _json_headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        api_key = self._api_key()
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        return headers

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        query: dict[str, Any] | None = None,
    ) -> Any:
        """Replace this adapter with the provider's HTTP client.

        A real provider can use requests/httpx here and keep the public provider
        methods below unchanged. The default template raises so installing this
        example cannot accidentally call a placeholder upstream.
        """
        raise NotImplementedError("replace TemplateTempMailProvider._request_json with provider HTTP calls")

        # Example implementation shape:
        # import requests
        # response = requests.request(
        #     method,
        #     f"{self._api_base_url()}{path}",
        #     headers=self._json_headers(),
        #     json=payload,
        #     params=query,
        #     timeout=REQUEST_TIMEOUT_SECONDS,
        # )
        # response.raise_for_status()
        # return response.json()

    def _normalize_domain(self, value: Any, *, default: bool = False) -> dict[str, Any] | None:
        if isinstance(value, dict):
            name = str(value.get("name") or value.get("domain") or "").strip()
            enabled = bool(value.get("enabled", value.get("isActive", True)))
        else:
            name = str(value or "").strip()
            enabled = True
        if not name:
            return None
        return {"name": name, "enabled": enabled, "is_default": default}

    def _normalize_message(self, raw_message: dict[str, Any]) -> dict[str, Any] | None:
        raw_id = str(raw_message.get("id") or raw_message.get("message_id") or "").strip()
        if not raw_id:
            return None

        html_content = str(raw_message.get("html") or raw_message.get("html_content") or "")
        text_content = str(raw_message.get("text") or raw_message.get("content") or raw_message.get("body") or "")
        return {
            "id": f"{PROVIDER_KEY}_{raw_id}",
            "message_id": f"{PROVIDER_KEY}_{raw_id}",
            "from_address": str(raw_message.get("from") or raw_message.get("from_address") or ""),
            "subject": str(raw_message.get("subject") or ""),
            "content": text_content,
            "html_content": html_content,
            "has_html": bool(html_content),
            "timestamp": int(raw_message.get("timestamp") or 0),
            "created_at": str(raw_message.get("created_at") or raw_message.get("date") or ""),
            "raw_content": json.dumps(raw_message, ensure_ascii=False, separators=(",", ":")),
        }

    def _to_raw_message_id(self, message_id: str) -> str:
        text = str(message_id or "").strip()
        prefix = f"{PROVIDER_KEY}_"
        return text[len(prefix) :] if text.startswith(prefix) else text

    def _mailbox_meta(self, mailbox: dict[str, Any] | str) -> dict[str, Any]:
        if not isinstance(mailbox, dict):
            return {}
        meta = mailbox.get("meta") or {}
        if isinstance(meta, dict):
            return meta
        if isinstance(meta, str):
            try:
                parsed = json.loads(meta)
                return parsed if isinstance(parsed, dict) else {}
            except Exception:
                return {}
        return {}

    def _mailbox_id(self, mailbox: dict[str, Any] | str) -> str:
        meta = self._mailbox_meta(mailbox)
        if meta.get("provider_mailbox_id"):
            return str(meta.get("provider_mailbox_id") or "").strip()
        if isinstance(mailbox, dict):
            return str(mailbox.get("email") or "").strip()
        return str(mailbox or "").strip()

    def get_options(self) -> dict[str, Any]:
        configured = bool(self._api_key())
        return {
            "domain_strategy": "auto_or_manual",
            "default_mode": "manual",
            "domains": [{"name": DEFAULT_DOMAIN, "enabled": True, "is_default": True}],
            "prefix_rules": {
                "min_length": 1,
                "max_length": 64,
                "pattern": r"^[a-z0-9][a-z0-9._-]*$",
            },
            "provider": self.provider_name,
            "provider_name": self.provider_name,
            "provider_label": self.provider_label,
            "api_base_url": self._api_base_url(),
            "configured": configured,
            "missing_config": [] if configured else ["api_key"],
        }

    def create_mailbox(self, *, prefix: str | None = None, domain: str | None = None) -> dict[str, Any]:
        if not self._api_key():
            return {
                "success": False,
                "error": "Template provider API key is not configured",
                "error_code": "TEMP_MAIL_PROVIDER_NOT_CONFIGURED",
            }

        payload = {"prefix": str(prefix or "").strip(), "domain": str(domain or "").strip()}
        try:
            data = self._request_json("POST", "/mailboxes", payload={key: value for key, value in payload.items() if value})
        except NotImplementedError as exc:
            return {"success": False, "error": str(exc), "error_code": "UPSTREAM_ADAPTER_NOT_IMPLEMENTED"}

        if not isinstance(data, dict):
            return {
                "success": False,
                "error": "create mailbox response must be an object",
                "error_code": "UPSTREAM_BAD_PAYLOAD",
            }

        email = str(data.get("email") or data.get("address") or "").strip()
        if not email:
            return {"success": False, "error": "create mailbox response missing email", "error_code": "UPSTREAM_BAD_PAYLOAD"}

        mailbox_id = str(data.get("id") or data.get("mailbox_id") or email).strip()
        return {
            "success": True,
            "email": email,
            "provider_name": self.provider_name,
            "meta": {
                "provider_name": self.provider_name,
                "provider_mailbox_id": mailbox_id,
                "provider_cursor": str(data.get("cursor") or ""),
                "provider_labels": [],
                "provider_capabilities": self.get_capabilities(),
            },
        }

    def delete_mailbox(self, mailbox: dict[str, Any]) -> bool:
        mailbox_id = self._mailbox_id(mailbox)
        if not mailbox_id or not self._api_key():
            return False
        try:
            self._request_json("DELETE", f"/mailboxes/{quote(mailbox_id, safe='')}")
            return True
        except NotImplementedError:
            return False

    def list_messages(self, mailbox: dict[str, Any]) -> list[dict[str, Any]] | None:
        mailbox_id = self._mailbox_id(mailbox)
        if not mailbox_id:
            return []
        data = self._request_json("GET", f"/mailboxes/{quote(mailbox_id, safe='')}/messages")
        raw_messages = data.get("messages") if isinstance(data, dict) else data
        if not isinstance(raw_messages, list):
            return []
        messages: list[dict[str, Any]] = []
        for item in raw_messages:
            if isinstance(item, dict):
                normalized = self._normalize_message(item)
                if normalized is not None:
                    messages.append(normalized)
        return messages

    def get_message_detail(self, mailbox: dict[str, Any], message_id: str) -> dict[str, Any] | None:
        mailbox_id = self._mailbox_id(mailbox)
        raw_id = self._to_raw_message_id(message_id)
        if not mailbox_id or not raw_id:
            return None
        data = self._request_json("GET", f"/mailboxes/{quote(mailbox_id, safe='')}/messages/{quote(raw_id, safe='')}")
        return self._normalize_message(data) if isinstance(data, dict) else None

    def delete_message(self, mailbox: dict[str, Any], message_id: str) -> bool:
        mailbox_id = self._mailbox_id(mailbox)
        raw_id = self._to_raw_message_id(message_id)
        if not mailbox_id or not raw_id or not self._api_key():
            return False
        try:
            self._request_json("DELETE", f"/mailboxes/{quote(mailbox_id, safe='')}/messages/{quote(raw_id, safe='')}")
            return True
        except NotImplementedError:
            return False

    def clear_messages(self, mailbox: dict[str, Any]) -> bool:
        messages = self.list_messages(mailbox) or []
        for item in messages:
            message_id = str(item.get("message_id") or item.get("id") or "").strip()
            if message_id and not self.delete_message(mailbox, message_id):
                return False
        return True
