from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

PROVIDER_KEY = "template_temp_mail"
MODULE_NAME = "_example_temp_mail_provider_plugin_template_test"
TEMPLATE_PATH = Path(__file__).resolve().parents[1] / "examples" / "temp_mail_provider_plugin_template.py"


class TempMailProviderPluginTemplateTests(unittest.TestCase):
    def setUp(self):
        from outlook_web.services.temp_mail_provider_base import _REGISTRY

        self._registry = _REGISTRY
        self._missing = object()
        self._previous_provider = self._registry.get(PROVIDER_KEY, self._missing)
        self._registry.pop(PROVIDER_KEY, None)
        sys.modules.pop(MODULE_NAME, None)

    def tearDown(self):
        self._registry.pop(PROVIDER_KEY, None)
        if self._previous_provider is not self._missing:
            self._registry[PROVIDER_KEY] = self._previous_provider
        sys.modules.pop(MODULE_NAME, None)

    def _load_template_module(self):
        spec = importlib.util.spec_from_file_location(MODULE_NAME, TEMPLATE_PATH)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader if spec is not None else None)
        module = importlib.util.module_from_spec(spec)
        sys.modules[MODULE_NAME] = module
        spec.loader.exec_module(module)  # type: ignore[union-attr]
        return module

    def test_template_import_registers_expected_provider_key(self):
        module = self._load_template_module()

        self.assertIn(PROVIDER_KEY, self._registry)
        self.assertIs(self._registry[PROVIDER_KEY], module.TemplateTempMailProvider)
        self.assertEqual(module.TemplateTempMailProvider.provider_name, PROVIDER_KEY)

    def test_template_contract_validation_is_valid_and_secret_safe(self):
        from outlook_web.services.temp_mail_provider_base import TempMailProviderBase
        from outlook_web.services.temp_mail_provider_contract import validate_temp_mail_provider_class

        module = self._load_template_module()

        self.assertTrue(issubclass(module.TemplateTempMailProvider, TempMailProviderBase))

        with patch.object(
            module.TemplateTempMailProvider,
            "_request_json",
            side_effect=AssertionError("network probe not allowed"),
        ):
            validation = validate_temp_mail_provider_class(
                PROVIDER_KEY,
                module.TemplateTempMailProvider,
                probe_options=True,
            )

        self.assertTrue(validation["valid"])
        self.assertEqual(validation["status"], "valid")
        self.assertEqual(validation["issues"], [])
        self.assertEqual(validation["summary"]["errors"], 0)
        self.assertEqual(validation["summary"]["warnings"], 0)
        checks = {check["key"]: check for check in validation["checks"]}
        self.assertTrue(checks["base_class"]["ok"])
        self.assertTrue(validation["safe_metadata"]["options_probe"]["ok"])

        fields = {field["key"]: field for field in validation["safe_metadata"]["config_fields"]}
        self.assertIn("api_key", fields)
        self.assertTrue(fields["api_key"]["secret"])
        self.assertNotIn("default", fields["api_key"])
        self.assertNotIn("example-secret", str(validation))
        self.assertNotIn("api_key_value", str(validation))
        self.assertNotIn("bearer-token-placeholder", str(validation))

    def test_template_can_be_completed_by_replacing_request_adapter(self):
        module = self._load_template_module()

        class LocalAdapterProvider(module.TemplateTempMailProvider):
            def _request_json(
                self,
                method: str,
                path: str,
                *,
                payload: dict[str, Any] | None = None,
                query: dict[str, Any] | None = None,
            ) -> Any:
                if method == "POST" and path == "/mailboxes":
                    return {"id": "mailbox-1", "email": "demo@example.test", "cursor": "cursor-1"}
                if method == "GET" and path == "/mailboxes/mailbox-1/messages":
                    return {
                        "messages": [
                            {
                                "id": "message-1",
                                "from": "sender@example.test",
                                "subject": "Hello",
                                "text": "Body",
                                "timestamp": 123,
                            }
                        ]
                    }
                if method == "GET" and path == "/mailboxes/mailbox-1/messages/message-1":
                    return {"id": "message-1", "from": "sender@example.test", "subject": "Hello", "text": "Body"}
                if method == "DELETE":
                    return {"ok": True}
                return {}

        provider = LocalAdapterProvider(
            provider_name=PROVIDER_KEY,
            config={"api_base_url": "https://api.local.test", "api_key": "configured-for-test"},
        )

        created = provider.create_mailbox(prefix="demo", domain="example.test")
        self.assertTrue(created["success"])
        self.assertEqual(created["email"], "demo@example.test")
        self.assertEqual(created["provider_name"], PROVIDER_KEY)
        self.assertEqual(created["meta"]["provider_mailbox_id"], "mailbox-1")
        self.assertTrue(created["meta"]["provider_capabilities"]["delete_mailbox"])

        mailbox = {"email": created["email"], "meta": created["meta"]}
        messages = provider.list_messages(mailbox)
        self.assertEqual(len(messages or []), 1)
        self.assertEqual(messages[0]["message_id"], f"{PROVIDER_KEY}_message-1")

        detail = provider.get_message_detail(mailbox, f"{PROVIDER_KEY}_message-1")
        self.assertIsNotNone(detail)
        self.assertEqual(detail["subject"], "Hello")
        self.assertTrue(provider.delete_message(mailbox, f"{PROVIDER_KEY}_message-1"))
        self.assertTrue(provider.delete_mailbox(mailbox))


if __name__ == "__main__":
    unittest.main()
