from __future__ import annotations

import unittest

from tests._import_app import import_web_app_module


class TempMailProviderFallbackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = import_web_app_module()
        cls.app = cls.module.app

    def test_uninstalled_legacy_bridge_falls_back_to_cloudflare(self):
        with self.app.app_context():
            from mailops.repositories import settings as settings_repo
            from mailops.services.temp_mail_public_plugins import (
                GPTMAIL_PLUGIN_PROVIDER_NAMES,
                OFFICIAL_PUBLIC_PROVIDER_NAMES,
            )
            from mailops.temp_mail_registry import _REGISTRY

            # Simulate production without official plugins registered.
            for name in list(_REGISTRY):
                if name in OFFICIAL_PUBLIC_PROVIDER_NAMES or name in GPTMAIL_PLUGIN_PROVIDER_NAMES:
                    _REGISTRY.pop(name, None)

            settings_repo.set_setting("temp_mail_provider", "legacy_bridge")
            resolved = settings_repo.get_temp_mail_provider(strict=False)
            self.assertEqual(resolved, "cloudflare_temp_mail")

            runtime = settings_repo.get_temp_mail_runtime_provider_name("legacy_bridge")
            self.assertEqual(runtime, "cloudflare_temp_mail")

            from mailops.services.temp_mail_provider_factory import get_temp_mail_provider

            provider = get_temp_mail_provider()
            self.assertEqual(provider.provider_name, "cloudflare_temp_mail")


if __name__ == "__main__":
    unittest.main()
