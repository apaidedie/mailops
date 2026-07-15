from __future__ import annotations

import unittest
from unittest.mock import patch

from tests._import_app import clear_login_attempts, import_web_app_module


class TempMailProviderFactoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = import_web_app_module()
        cls.app = cls.module.app

    def setUp(self):
        with self.app.app_context():
            clear_login_attempts()
            from outlook_web.repositories import settings as settings_repo

            settings_repo.set_setting("temp_mail_provider", "custom_domain_temp_mail")

    def test_factory_returns_provider_from_formal_settings(self):
        with self.app.app_context():
            from outlook_web.services.temp_mail_provider_custom import CustomTempMailProvider
            from outlook_web.services.temp_mail_provider_factory import get_temp_mail_provider

            provider = get_temp_mail_provider()

        self.assertIsInstance(provider, CustomTempMailProvider)
        self.assertEqual(provider.provider_name, "custom_domain_temp_mail")

    def test_factory_uses_temp_mail_provider_environment_override(self):
        with self.app.app_context():
            from outlook_web.repositories import settings as settings_repo
            from outlook_web.services.temp_mail_provider_factory import get_temp_mail_provider

            settings_repo.set_setting("temp_mail_provider", "custom_domain_temp_mail")
            with patch.dict("os.environ", {"TEMP_MAIL_PROVIDER": "mail_tm"}):
                provider = get_temp_mail_provider()

        self.assertEqual(provider.provider_name, "mail_tm")

    def test_explicit_provider_argument_takes_priority_over_environment_override(self):
        with self.app.app_context():
            from outlook_web.services.temp_mail_provider_factory import get_temp_mail_provider

            with patch.dict("os.environ", {"TEMP_MAIL_PROVIDER": "mail_tm"}):
                provider = get_temp_mail_provider("tempmail_lol")

        self.assertEqual(provider.provider_name, "tempmail_lol")

    def test_factory_normalizes_legacy_provider_name_to_internal_bridge(self):
        with self.app.app_context():
            from outlook_web.services.temp_mail_provider_factory import get_temp_mail_provider

            provider = get_temp_mail_provider("legacy_gptmail")

        self.assertEqual(provider.provider_name, "legacy_bridge")

    def test_factory_normalizes_temp_mail_alias_to_internal_bridge(self):
        with self.app.app_context():
            from outlook_web.services.temp_mail_provider_factory import get_temp_mail_provider

            provider = get_temp_mail_provider("temp_mail")

        self.assertEqual(provider.provider_name, "legacy_bridge")

    def test_factory_rejects_invalid_provider_name(self):
        with self.app.app_context():
            from outlook_web.services.temp_mail_provider_factory import (
                TempMailProviderFactoryError,
                get_temp_mail_provider,
            )

            with self.assertRaises(TempMailProviderFactoryError) as ctx:
                get_temp_mail_provider("unknown-provider")

        self.assertEqual(ctx.exception.code, "TEMP_MAIL_PROVIDER_INVALID")
