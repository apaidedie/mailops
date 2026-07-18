from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path


class ProviderDevKitTests(unittest.TestCase):
    def test_scaffold_command_outputs_json_and_generates_plugin(self):
        from scripts import provider_dev_kit

        with tempfile.TemporaryDirectory(prefix="provider-dev-kit-") as tmpdir:
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                exit_code = provider_dev_kit.main(["scaffold", "sample_bridge", "--output-dir", tmpdir, "--format", "json"])

            payload = json.loads(buffer.getvalue())
            target = Path(payload["file_path"])

        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["tool"], "provider-dev-kit")
        self.assertEqual(payload["command"], "scaffold")
        self.assertEqual(payload["provider"], "sample_bridge")
        self.assertEqual(payload["class_name"], "SampleBridgeTempMailProvider")
        self.assertEqual(payload["secret_scan"], {"ok": True, "hits": []})
        self.assertTrue(target.name.endswith("sample_bridge.py"))
        self.assertIn("provider_dev_kit.py validate sample_bridge", "\n".join(payload["next_steps"]))

    def test_validate_command_is_offline_by_default_and_outputs_contract_json(self):
        from mailops.services.temp_mail_provider_base import _REGISTRY
        from scripts import provider_dev_kit

        provider_key = "offline_contract"
        previous_provider = _REGISTRY.get(provider_key)
        _REGISTRY.pop(provider_key, None)

        plugin_source = """from mailops.services.temp_mail_provider_base import TempMailProviderBase, register_provider

@register_provider
class OfflineContractProvider(TempMailProviderBase):
    provider_name = "offline_contract"
    provider_label = "Offline Contract"
    provider_version = "1.0.0"
    def get_options(self):
        raise RuntimeError("get_options should not run by default")
    def create_mailbox(self, *, prefix=None, domain=None): return {}
    def delete_mailbox(self, mailbox): return True
    def list_messages(self, mailbox): return []
    def get_message_detail(self, mailbox, message_id): return None
    def delete_message(self, mailbox, message_id): return True
    def clear_messages(self, mailbox): return True
"""

        with tempfile.TemporaryDirectory(prefix="provider-dev-kit-") as tmpdir:
            target = Path(tmpdir) / "offline_contract.py"
            target.write_text(plugin_source, encoding="utf-8")
            buffer = io.StringIO()
            try:
                with redirect_stdout(buffer):
                    exit_code = provider_dev_kit.main(["validate", provider_key, "--file", str(target), "--format", "json"])
            finally:
                _REGISTRY.pop(provider_key, None)
                if previous_provider is not None:
                    _REGISTRY[provider_key] = previous_provider
                sys.modules.pop(f"_plugin_validate_{provider_key}", None)

        payload = json.loads(buffer.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertFalse(payload["probe_options"])
        self.assertEqual(payload["contract_validation"]["status"], "valid")
        self.assertEqual(payload["contract_validation"]["safe_metadata"]["options_probe"], {"requested": False, "ok": None})
        self.assertEqual(payload["secret_scan"], {"ok": True, "hits": []})

    def test_validate_command_fails_on_secret_scan_without_leaking_value(self):
        from mailops.services.temp_mail_provider_base import _REGISTRY
        from scripts import provider_dev_kit

        provider_key = "secret_scan_contract"
        previous_provider = _REGISTRY.get(provider_key)
        _REGISTRY.pop(provider_key, None)
        secret_value = "dk_" + "a" * 64
        plugin_source = f"""from mailops.services.temp_mail_provider_base import TempMailProviderBase, register_provider

TOKEN_EXAMPLE = "{secret_value}"

@register_provider
class SecretScanContractProvider(TempMailProviderBase):
    provider_name = "secret_scan_contract"
    provider_label = "Secret Scan Contract"
    provider_version = "1.0.0"
    def get_options(self): return {{"domains": []}}
    def create_mailbox(self, *, prefix=None, domain=None): return {{}}
    def delete_mailbox(self, mailbox): return True
    def list_messages(self, mailbox): return []
    def get_message_detail(self, mailbox, message_id): return None
    def delete_message(self, mailbox, message_id): return True
    def clear_messages(self, mailbox): return True
"""

        with tempfile.TemporaryDirectory(prefix="provider-dev-kit-") as tmpdir:
            target = Path(tmpdir) / "secret_scan_contract.py"
            target.write_text(plugin_source, encoding="utf-8")
            buffer = io.StringIO()
            try:
                with redirect_stdout(buffer):
                    exit_code = provider_dev_kit.main(["validate", provider_key, "--file", str(target), "--format", "json"])
            finally:
                _REGISTRY.pop(provider_key, None)
                if previous_provider is not None:
                    _REGISTRY[provider_key] = previous_provider
                sys.modules.pop(f"_plugin_validate_{provider_key}", None)

        output = buffer.getvalue()
        payload = json.loads(output)
        self.assertEqual(exit_code, 2)
        self.assertFalse(payload["success"])
        self.assertEqual(payload["contract_validation"]["status"], "valid")
        self.assertFalse(payload["secret_scan"]["ok"])
        self.assertEqual(payload["secret_scan"]["hits"][0]["pattern"], "duckmail_bearer_token")
        self.assertNotIn(secret_value, output)

    def test_probe_options_is_explicit(self):
        from mailops.services.temp_mail_provider_base import _REGISTRY
        from scripts import provider_dev_kit

        provider_key = "probe_contract"
        previous_provider = _REGISTRY.get(provider_key)
        _REGISTRY.pop(provider_key, None)
        plugin_source = """from mailops.services.temp_mail_provider_base import TempMailProviderBase, register_provider

@register_provider
class ProbeContractProvider(TempMailProviderBase):
    provider_name = "probe_contract"
    provider_label = "Probe Contract"
    provider_version = "1.0.0"
    def get_options(self):
        raise RuntimeError("probe was requested")
    def create_mailbox(self, *, prefix=None, domain=None): return {}
    def delete_mailbox(self, mailbox): return True
    def list_messages(self, mailbox): return []
    def get_message_detail(self, mailbox, message_id): return None
    def delete_message(self, mailbox, message_id): return True
    def clear_messages(self, mailbox): return True
"""

        with tempfile.TemporaryDirectory(prefix="provider-dev-kit-") as tmpdir:
            target = Path(tmpdir) / "probe_contract.py"
            target.write_text(plugin_source, encoding="utf-8")
            buffer = io.StringIO()
            try:
                with redirect_stdout(buffer):
                    exit_code = provider_dev_kit.main(
                        ["validate", provider_key, "--file", str(target), "--probe-options", "--format", "json"]
                    )
            finally:
                _REGISTRY.pop(provider_key, None)
                if previous_provider is not None:
                    _REGISTRY[provider_key] = previous_provider
                sys.modules.pop(f"_plugin_validate_{provider_key}", None)

        payload = json.loads(buffer.getvalue())
        self.assertEqual(exit_code, 2)
        self.assertFalse(payload["success"])
        self.assertTrue(payload["probe_options"])
        self.assertEqual(payload["contract_validation"]["status"], "warning")
        self.assertIn("OPTIONS_PROBE_FAILED", {issue["code"] for issue in payload["contract_validation"]["issues"]})


if __name__ == "__main__":
    unittest.main()
