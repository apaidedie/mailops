from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests._import_app import clear_login_attempts, import_web_app_module


class TempMailSettingsPlatformContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = import_web_app_module()
        cls.app = cls.module.app

    def setUp(self):
        with self.app.app_context():
            clear_login_attempts()
            from mailops.repositories import settings as settings_repo

            settings_repo.set_setting("temp_mail_provider", "custom_domain_temp_mail")
            settings_repo.set_setting("pool_default_provider", "")
            settings_repo.set_setting("active_mailbox_providers", "")
            settings_repo.set_setting("temp_mail_api_base_url", "https://platform-settings.test")
            settings_repo.set_setting("temp_mail_api_key", "platform-secret")
            settings_repo.set_setting("gptmail_api_key", "legacy-secret")
            settings_repo.set_setting(
                "temp_mail_domains",
                '[{"name":"settings-platform.test","enabled":true}]',
            )
            settings_repo.set_setting("temp_mail_default_domain", "settings-platform.test")
            settings_repo.set_setting(
                "temp_mail_prefix_rules",
                '{"min_length":2,"max_length":20,"pattern":"^[a-z0-9-]+$"}',
            )

    def _login(self, client):
        resp = client.post("/login", json={"password": "testpass123"})
        self.assertEqual(resp.status_code, 200)

    def test_get_settings_exposes_formal_temp_mail_fields_only(self):
        client = self.app.test_client()
        self._login(client)

        resp = client.get("/api/settings")

        self.assertEqual(resp.status_code, 200)
        settings = resp.get_json()["settings"]
        self.assertEqual(settings["temp_mail_provider"], "custom_domain_temp_mail")
        self.assertEqual(settings["temp_mail_provider_label"], "GPTMail")
        self.assertTrue(settings["temp_mail_api_key_set"])
        self.assertNotIn("gptmail_api_key_set", settings)
        self.assertEqual(settings["temp_mail_domains"][0]["name"], "settings-platform.test")

    def test_put_empty_temp_mail_api_key_does_not_clear_existing_value(self):
        client = self.app.test_client()
        self._login(client)

        resp = client.put("/api/settings", json={"temp_mail_api_key": ""})

        self.assertEqual(resp.status_code, 200)
        with self.app.app_context():
            from mailops.repositories import settings as settings_repo

            self.assertEqual(settings_repo.get_setting("temp_mail_api_key"), "platform-secret")
            self.assertEqual(settings_repo.get_setting("gptmail_api_key"), "legacy-secret")

    def test_db_settings_take_priority_over_env_fallback(self):
        with self.app.app_context():
            from mailops.repositories import settings as settings_repo

            with patch("mailops.config.get_temp_mail_api_key_default", return_value="env-secret"):
                value = settings_repo.get_temp_mail_api_key()

        self.assertEqual(value, "platform-secret")

    def test_runtime_provider_selection_matches_saved_formal_provider(self):
        with self.app.app_context():
            from mailops.repositories import settings as settings_repo
            from mailops.services.temp_mail_provider_factory import get_temp_mail_provider

            provider = get_temp_mail_provider()
            self.assertEqual(settings_repo.get_temp_mail_provider(), "custom_domain_temp_mail")
            self.assertEqual(provider.provider_name, "custom_domain_temp_mail")

    def test_get_settings_reflects_temp_mail_provider_environment_override(self):
        client = self.app.test_client()
        self._login(client)

        with patch.dict("os.environ", {"TEMP_MAIL_PROVIDER": "mail_tm"}):
            resp = client.get("/api/settings")

        self.assertEqual(resp.status_code, 200)
        settings = resp.get_json()["settings"]
        self.assertEqual(settings["temp_mail_provider"], "mail_tm")
        self.assertEqual(settings["temp_mail_provider_label"], "Mail.tm")

    def test_temp_mail_provider_environment_override_normalizes_legacy_alias(self):
        with self.app.app_context():
            from mailops.repositories import settings as settings_repo

            with patch.dict("os.environ", {"TEMP_MAIL_PROVIDER": "gptmail"}):
                provider = settings_repo.get_temp_mail_provider()

        self.assertEqual(provider, "legacy_bridge")

    def test_provider_config_file_overrides_saved_provider_settings(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "providers.json"
            config_path.write_text(
                '{"mailbox_providers":{"temp_mail_provider":"mail_tm","pool_default_provider":"mail_tm","active_mailbox_providers":["mail_tm","imap"]}}',
                encoding="utf-8",
            )

            with self.app.app_context():
                from mailops.repositories import settings as settings_repo

                with patch.dict("os.environ", {"OUTLOOK_EMAIL_PROVIDER_CONFIG_FILE": str(config_path)}, clear=False):
                    self.assertEqual(settings_repo.get_temp_mail_provider(), "mail_tm")
                    self.assertEqual(settings_repo.get_pool_default_provider(), "mail_tm")
                    self.assertEqual(settings_repo.get_active_mailbox_provider_names(), ["mail_tm", "imap"])

    def test_provider_config_file_supports_toml_and_env_takes_priority(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "providers.toml"
            config_path.write_text(
                '[mailbox_providers]\ntemp_mail_provider = "mail_tm"\npool_default_provider = "mail_tm"\nactive_mailbox_providers = ["mail_tm"]\n',
                encoding="utf-8",
            )

            with self.app.app_context():
                from mailops.repositories import settings as settings_repo

                with patch.dict(
                    "os.environ",
                    {
                        "OUTLOOK_EMAIL_PROVIDER_CONFIG_FILE": str(config_path),
                        "TEMP_MAIL_PROVIDER": "duckmail",
                    },
                    clear=False,
                ):
                    self.assertEqual(settings_repo.get_temp_mail_provider(), "duckmail")
                    self.assertEqual(settings_repo.get_pool_default_provider(), "mail_tm")
                    self.assertEqual(settings_repo.get_active_mailbox_provider_names(), ["mail_tm"])

    def test_provider_config_file_empty_active_allowlist_overrides_saved_allowlist(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "providers.json"
            config_path.write_text('{"providers":{"active_mailbox_providers":[]}}', encoding="utf-8")

            with self.app.app_context():
                from mailops.repositories import settings as settings_repo

                settings_repo.set_setting("active_mailbox_providers", "duckmail")
                with patch.dict("os.environ", {"OUTLOOK_EMAIL_PROVIDER_CONFIG_FILE": str(config_path)}, clear=False):
                    self.assertEqual(settings_repo.get_active_mailbox_provider_names(), [])

    def test_missing_provider_config_file_is_strict_at_runtime_and_non_strict_for_discovery(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            missing_config_path = Path(tmpdir) / "missing-providers.json"

            with self.app.app_context():
                from mailops import config
                from mailops.repositories import settings as settings_repo

                settings_repo.set_setting("active_mailbox_providers", "duckmail")
                with patch.dict(
                    "os.environ",
                    {
                        "OUTLOOK_EMAIL_PROVIDER_CONFIG_FILE": str(missing_config_path),
                        "TEMP_MAIL_PROVIDER": "",
                        "EXTERNAL_POOL_DEFAULT_PROVIDER": "",
                        "ACTIVE_MAILBOX_PROVIDERS": "",
                    },
                    clear=False,
                ):
                    with self.assertRaises(config.ProviderConfigFileError) as ctx:
                        settings_repo.get_temp_mail_provider()

                    status = config.get_provider_config_file_status()
                    self.assertEqual(ctx.exception.code, "PROVIDER_CONFIG_FILE_NOT_FOUND")
                    self.assertEqual(status["error_code"], "PROVIDER_CONFIG_FILE_NOT_FOUND")
                    self.assertFalse(status["loaded"])
                    self.assertEqual(settings_repo.get_temp_mail_provider(strict=False), "custom_domain_temp_mail")
                    self.assertEqual(settings_repo.get_pool_default_provider(strict=False), "")
                    self.assertEqual(settings_repo.get_active_mailbox_provider_names(strict=False), ["duckmail"])

    def test_get_settings_reports_missing_provider_config_file_without_failing(self):
        client = self.app.test_client()
        self._login(client)

        with tempfile.TemporaryDirectory() as tmpdir:
            missing_config_path = Path(tmpdir) / "missing-providers.json"
            with patch.dict(
                "os.environ",
                {
                    "OUTLOOK_EMAIL_PROVIDER_CONFIG_FILE": str(missing_config_path),
                    "TEMP_MAIL_PROVIDER": "",
                    "EXTERNAL_POOL_DEFAULT_PROVIDER": "",
                    "ACTIVE_MAILBOX_PROVIDERS": "",
                },
                clear=False,
            ):
                resp = client.get("/api/settings")

        self.assertEqual(resp.status_code, 200)
        settings = resp.get_json()["settings"]
        self.assertEqual(settings["temp_mail_provider"], "custom_domain_temp_mail")
        self.assertEqual(settings["pool_default_provider"], "auto")
        self.assertEqual(settings["provider_config_file"]["error_code"], "PROVIDER_CONFIG_FILE_NOT_FOUND")

    def test_put_rejects_invalid_temp_mail_provider_before_runtime(self):
        client = self.app.test_client()
        self._login(client)

        resp = client.put("/api/settings", json={"temp_mail_provider": "unknown-provider"})

        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertFalse(data["success"])
        self.assertEqual(data["error"]["code"], "TEMP_MAIL_PROVIDER_INVALID")

        with self.app.app_context():
            from mailops.repositories import settings as settings_repo

            self.assertEqual(settings_repo.get_setting("temp_mail_provider"), "custom_domain_temp_mail")
