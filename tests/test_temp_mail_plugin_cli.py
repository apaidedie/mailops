"""层 G：CLI 命令测试

验证 CLI 子命令的参数解析和核心调用。
"""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


class TestPluginCLI(unittest.TestCase):
    """TDD-G: CLI 命令"""

    def setUp(self):
        from tests._import_app import import_web_app_module

        self._app_mod = import_web_app_module()

    # G-CLI-01
    @patch("outlook_web.services.temp_mail_plugin_cli.install_plugin")
    @patch("outlook_web.services.temp_mail_plugin_cli._confirm", return_value=True)
    @patch("builtins.print")
    def test_cli_install_plugin(self, mock_print, mock_confirm, mock_install):
        """install-provider moemail 调用 install_plugin"""
        mock_install.return_value = {"plugin_name": "moemail", "file_path": "/tmp/moemail.py", "dependencies": []}

        from outlook_web.services.temp_mail_plugin_cli import _cmd_install

        _cmd_install("moemail", None)
        mock_install.assert_called_once_with("moemail", url=None)

    # G-CLI-02
    @patch("outlook_web.services.temp_mail_plugin_cli.install_plugin")
    @patch("outlook_web.services.temp_mail_plugin_cli._confirm", return_value=True)
    @patch("builtins.print")
    def test_cli_install_with_custom_url(self, mock_print, mock_confirm, mock_install):
        """install-provider moemail --from URL 传递 url"""
        mock_install.return_value = {"plugin_name": "moemail", "file_path": "/tmp/moemail.py", "dependencies": []}

        from outlook_web.services.temp_mail_plugin_cli import _cmd_install

        _cmd_install("moemail", "https://example.com/plugin.py")
        mock_install.assert_called_once_with("moemail", url="https://example.com/plugin.py")

    # G-CLI-03
    @patch("outlook_web.services.temp_mail_plugin_cli.uninstall_plugin")
    @patch("outlook_web.services.temp_mail_plugin_cli._confirm", return_value=True)
    @patch(
        "outlook_web.services.temp_mail_plugin_cli.check_provider_in_use", return_value={"task_count": 0, "active_count": 0}
    )
    @patch("builtins.print")
    def test_cli_uninstall_plugin(self, mock_print, mock_check, mock_confirm, mock_uninstall):
        """uninstall-provider moemail 调用 uninstall_plugin"""
        mock_uninstall.return_value = {"plugin_name": "moemail", "had_active_emails": False, "cleaned_keys": []}

        from outlook_web.services.temp_mail_plugin_cli import _cmd_uninstall

        _cmd_uninstall("moemail")
        mock_uninstall.assert_called_once()

    # G-CLI-04
    @patch("outlook_web.services.temp_mail_plugin_cli.get_available_providers")
    @patch("outlook_web.services.temp_mail_plugin_cli.get_installed_plugins")
    @patch("builtins.print")
    def test_cli_list_providers(self, mock_print, mock_installed, mock_available):
        """list-providers 输出包含内置 provider"""
        mock_installed.return_value = []
        mock_available.return_value = [
            {"name": "cloudflare_temp_mail", "label": "CF Worker", "version": "1.0.0"},
            {"name": "custom_domain_temp_mail", "label": "Compatible Temp Mail Bridge", "version": "1.0.0"},
        ]

        from outlook_web.services.temp_mail_plugin_cli import _cmd_list

        _cmd_list()
        printed = "\n".join(call.args[0] for call in mock_print.call_args_list if call.args)
        self.assertIn("cloudflare_temp_mail", printed)

    # G-CLI-05
    @patch("builtins.print")
    def test_cli_no_command_shows_help(self, mock_print):
        """无子命令时打印帮助信息"""
        import argparse

        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers(dest="command")
        sub.add_parser("install-provider")
        sub.add_parser("uninstall-provider")
        sub.add_parser("list-providers")

        args = parser.parse_args([])
        self.assertIsNone(args.command)

    # G-CLI-06
    @patch("outlook_web.services.temp_mail_plugin_cli.install_plugin")
    @patch("outlook_web.services.temp_mail_plugin_cli._confirm", return_value=True)
    @patch("builtins.print")
    def test_cli_install_with_dependencies_output(self, mock_print, mock_confirm, mock_install):
        """有依赖的插件输出包含依赖安装提示"""
        mock_install.return_value = {
            "plugin_name": "moemail",
            "file_path": "/tmp/moemail.py",
            "dependencies": ["moemail-sdk>=1.0"],
        }

        from outlook_web.services.temp_mail_plugin_cli import _cmd_install

        _cmd_install("moemail", None)
        printed = "\n".join(str(call.args[0]) for call in mock_print.call_args_list if call.args)
        self.assertIn("moemail-sdk", printed)

    def test_scaffold_provider_writes_valid_contract_plugin(self):
        from outlook_web.services.temp_mail_plugin_manager import scaffold_provider_plugin
        from outlook_web.services.temp_mail_provider_base import _REGISTRY, TempMailProviderBase
        from outlook_web.services.temp_mail_provider_contract import validate_temp_mail_provider_class

        provider_key = "example_bridge"
        module_name = "_scaffold_example_bridge_test"
        previous_provider = _REGISTRY.get(provider_key)
        _REGISTRY.pop(provider_key, None)
        sys.modules.pop(module_name, None)

        with tempfile.TemporaryDirectory(prefix="provider-scaffold-") as tmpdir:
            result = scaffold_provider_plugin(provider_key, output_dir=tmpdir)
            target = Path(result["file_path"])

            self.assertTrue(target.exists())
            self.assertEqual(target.name, "example_bridge.py")
            self.assertEqual(result["class_name"], "ExampleBridgeTempMailProvider")
            content = target.read_text(encoding="utf-8")
            self.assertIn('PROVIDER_KEY = "example_bridge"', content)
            self.assertIn("class ExampleBridgeTempMailProvider", content)
            self.assertIn('provider_label = "Example Bridge"', content)
            self.assertNotIn('PROVIDER_KEY = "template_temp_mail"', content)

            try:
                spec = importlib.util.spec_from_file_location(module_name, target)
                self.assertIsNotNone(spec)
                self.assertIsNotNone(spec.loader if spec is not None else None)
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)  # type: ignore[union-attr]

                provider_cls = _REGISTRY[provider_key]
                self.assertTrue(issubclass(provider_cls, TempMailProviderBase))
                validation = validate_temp_mail_provider_class(provider_key, provider_cls, probe_options=True)
                self.assertTrue(validation["valid"])
                self.assertEqual(validation["status"], "valid")
                self.assertEqual(validation["summary"]["errors"], 0)
                self.assertNotIn("example-secret", str(validation))
            finally:
                _REGISTRY.pop(provider_key, None)
                if previous_provider is not None:
                    _REGISTRY[provider_key] = previous_provider
                sys.modules.pop(module_name, None)

    def test_scaffold_provider_rejects_invalid_key(self):
        from outlook_web.services.temp_mail_plugin_manager import PluginManagerError, scaffold_provider_plugin

        with tempfile.TemporaryDirectory(prefix="provider-scaffold-") as tmpdir:
            with self.assertRaises(PluginManagerError) as ctx:
                scaffold_provider_plugin("bad provider", output_dir=tmpdir)

        self.assertEqual(ctx.exception.code, "PLUGIN_PROVIDER_KEY_INVALID")

    def test_scaffold_provider_refuses_overwrite_without_force(self):
        from outlook_web.services.temp_mail_plugin_manager import PluginManagerError, scaffold_provider_plugin

        with tempfile.TemporaryDirectory(prefix="provider-scaffold-") as tmpdir:
            target = Path(tmpdir) / "existing_provider.py"
            target.write_text("original", encoding="utf-8")

            with self.assertRaises(PluginManagerError) as ctx:
                scaffold_provider_plugin("existing_provider", output_dir=tmpdir)

            self.assertEqual(ctx.exception.code, "PLUGIN_SCAFFOLD_EXISTS")
            self.assertEqual(target.read_text(encoding="utf-8"), "original")

    def test_scaffold_provider_force_overwrites_existing_file(self):
        from outlook_web.services.temp_mail_plugin_manager import scaffold_provider_plugin

        with tempfile.TemporaryDirectory(prefix="provider-scaffold-") as tmpdir:
            target = Path(tmpdir) / "existing_provider.py"
            target.write_text("original", encoding="utf-8")

            result = scaffold_provider_plugin("existing_provider", output_dir=tmpdir, force=True)

            self.assertEqual(Path(result["file_path"]), target)
            self.assertTrue(result["overwritten"])
            self.assertIn('PROVIDER_KEY = "existing_provider"', target.read_text(encoding="utf-8"))

    @patch("outlook_web.services.temp_mail_plugin_cli.scaffold_provider_plugin")
    @patch("builtins.print")
    def test_cli_scaffold_provider(self, mock_print, mock_scaffold):
        mock_scaffold.return_value = {
            "plugin_name": "example_bridge",
            "file_path": "/tmp/example_bridge.py",
            "class_name": "ExampleBridgeTempMailProvider",
        }

        from outlook_web.services.temp_mail_plugin_cli import _cmd_scaffold

        result = _cmd_scaffold("example_bridge", "/tmp", True)

        self.assertEqual(result, 0)
        mock_scaffold.assert_called_once_with("example_bridge", output_dir="/tmp", force=True)
        printed = "\n".join(str(call.args[0]) for call in mock_print.call_args_list if call.args)
        self.assertIn("example_bridge", printed)
        self.assertIn("reload-plugins", printed)

    @patch("builtins.print")
    def test_cli_validate_provider_file_outputs_valid_json(self, mock_print):
        from outlook_web.services.temp_mail_plugin_cli import _cmd_validate_provider
        from outlook_web.services.temp_mail_provider_base import _REGISTRY

        provider_key = "template_temp_mail"
        previous_provider = _REGISTRY.get(provider_key)
        _REGISTRY.pop(provider_key, None)

        try:
            result = _cmd_validate_provider(
                provider_key,
                "examples/temp_mail_provider_plugin_template.py",
                probe_options=True,
            )
        finally:
            _REGISTRY.pop(provider_key, None)
            if previous_provider is not None:
                _REGISTRY[provider_key] = previous_provider
            sys.modules.pop("_plugin_validate_template_temp_mail", None)

        self.assertEqual(result, 0)
        payload = json.loads(mock_print.call_args.args[0])
        self.assertEqual(payload["provider"], provider_key)
        self.assertEqual(payload["contract_validation"]["status"], "valid")
        self.assertEqual(payload["contract_validation"]["summary"]["errors"], 0)

    @patch("builtins.print")
    def test_cli_validate_provider_registered_provider_without_file(self, mock_print):
        from outlook_web.services.temp_mail_plugin_cli import _cmd_validate_provider
        from outlook_web.services.temp_mail_provider_base import _REGISTRY, TempMailProviderBase, register_provider

        provider_key = "registered_contract"
        previous_provider = _REGISTRY.get(provider_key)
        _REGISTRY.pop(provider_key, None)

        @register_provider
        class RegisteredContractProvider(TempMailProviderBase):
            provider_name = provider_key
            provider_label = "Registered Contract"
            provider_version = "1.0.0"

            def get_options(self):
                return {"domains": []}

            def create_mailbox(self, *, prefix=None, domain=None):
                return {}

            def delete_mailbox(self, mailbox):
                return True

            def list_messages(self, mailbox):
                return []

            def get_message_detail(self, mailbox, message_id):
                return None

            def delete_message(self, mailbox, message_id):
                return True

            def clear_messages(self, mailbox):
                return True

        try:
            result = _cmd_validate_provider(provider_key, None, probe_options=True)
        finally:
            _REGISTRY.pop(provider_key, None)
            if previous_provider is not None:
                _REGISTRY[provider_key] = previous_provider

        self.assertEqual(result, 0)
        payload = json.loads(mock_print.call_args.args[0])
        self.assertEqual(payload["source"], "registry")
        self.assertEqual(payload["contract_validation"]["status"], "valid")

    @patch("builtins.print")
    def test_cli_validate_provider_secret_default_exits_nonzero_without_leaking_secret(self, mock_print):
        from outlook_web.services.temp_mail_plugin_cli import _cmd_validate_provider
        from outlook_web.services.temp_mail_provider_base import _REGISTRY

        provider_key = "leaky_contract"
        module_name = "_plugin_validate_leaky_contract"
        previous_provider = _REGISTRY.get(provider_key)
        _REGISTRY.pop(provider_key, None)
        sys.modules.pop(module_name, None)

        plugin_source = """from outlook_web.services.temp_mail_provider_base import TempMailProviderBase, register_provider

@register_provider
class LeakyContractProvider(TempMailProviderBase):
    provider_name = "leaky_contract"
    provider_label = "Leaky Contract"
    provider_version = "1.0.0"
    config_schema = {"fields": [{"key": "api_key", "type": "password", "default": "secret-value-123"}]}
    def get_options(self): return {"domains": []}
    def create_mailbox(self, *, prefix=None, domain=None): return {}
    def delete_mailbox(self, mailbox): return True
    def list_messages(self, mailbox): return []
    def get_message_detail(self, mailbox, message_id): return None
    def delete_message(self, mailbox, message_id): return True
    def clear_messages(self, mailbox): return True
"""

        with tempfile.TemporaryDirectory(prefix="provider-validate-") as tmpdir:
            target = Path(tmpdir) / "leaky_contract.py"
            target.write_text(plugin_source, encoding="utf-8")
            try:
                result = _cmd_validate_provider(provider_key, str(target), probe_options=False)
            finally:
                _REGISTRY.pop(provider_key, None)
                if previous_provider is not None:
                    _REGISTRY[provider_key] = previous_provider
                sys.modules.pop(module_name, None)

        self.assertEqual(result, 2)
        printed = "\n".join(str(call.args[0]) for call in mock_print.call_args_list if call.args)
        self.assertIn('"status": "invalid"', printed)
        self.assertIn("CONFIG_FIELD_SECRET_DEFAULT", printed)
        self.assertNotIn("secret-value-123", printed)

    @patch("builtins.print")
    def test_cli_validate_provider_unknown_registered_provider_returns_error(self, mock_print):
        from outlook_web.services.temp_mail_plugin_cli import _cmd_validate_provider

        result = _cmd_validate_provider("missing_provider_for_validation", None, probe_options=True)

        self.assertEqual(result, 1)
        payload = json.loads(mock_print.call_args.args[0])
        self.assertFalse(payload["success"])
        self.assertEqual(payload["code"], "PLUGIN_NOT_LOADED")


if __name__ == "__main__":
    unittest.main()
