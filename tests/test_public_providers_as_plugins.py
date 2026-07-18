from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from tests._import_app import import_web_app_module


class PublicProvidersAsPluginsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = import_web_app_module()
        cls.app = cls.module.app

    def test_available_plugins_include_official_public_services(self):
        from mailops.services.temp_mail_plugin_manager import get_available_plugins

        names = {str(item.get("name") or "") for item in get_available_plugins()}
        self.assertTrue({"mail_tm", "duckmail", "tempmail_lol", "emailnator"}.issubset(names))

    def test_install_bundled_mail_tm_plugin_copies_file(self):
        from mailops.services import temp_mail_plugin_manager as plugin_manager

        with self.app.app_context():
            plugin_dir = plugin_manager._ensure_plugin_dir()
            target = plugin_dir / "mail_tm.py"
            if target.exists():
                target.unlink()

            result = plugin_manager.install_plugin("mail_tm")
            self.assertEqual(result.get("plugin_name"), "mail_tm")
            self.assertTrue(target.is_file())
            text = target.read_text(encoding="utf-8")
            self.assertIn("register_official_public_providers", text)

            # cleanup installed file for isolation (tests may re-register via conftest)
            target.unlink(missing_ok=True)

    def test_bundled_plugin_dir_exists(self):
        from mailops.services.temp_mail_plugin_manager import _get_bundled_plugin_dir

        bundled = _get_bundled_plugin_dir()
        self.assertTrue(bundled.is_dir(), msg=str(bundled))
        for name in ("mail_tm.py", "duckmail.py", "tempmail_lol.py", "emailnator.py"):
            self.assertTrue((bundled / name).is_file(), msg=name)


if __name__ == "__main__":
    unittest.main()
