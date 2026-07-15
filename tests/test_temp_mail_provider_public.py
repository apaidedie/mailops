from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from tests._import_app import clear_login_attempts, import_web_app_module


def _response(*, ok: bool = True, status_code: int = 200, payload=None, text: str = ""):
    resp = MagicMock()
    resp.ok = ok
    resp.status_code = status_code
    resp.text = text
    resp.reason = text
    resp.json.return_value = payload if payload is not None else {}
    return resp


class PublicTempMailProviderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = import_web_app_module()
        cls.app = cls.module.app

    def setUp(self):
        with self.app.app_context():
            clear_login_attempts()
            from outlook_web.db import get_db
            from outlook_web.repositories import settings as settings_repo

            db = get_db()
            db.execute("DELETE FROM temp_email_messages WHERE email_address LIKE '%@public-provider.test'")
            db.execute("DELETE FROM temp_emails WHERE email LIKE '%@public-provider.test'")
            db.commit()
            settings_repo.set_setting("temp_mail_provider", "custom_domain_temp_mail")
            settings_repo.set_setting("emailnator_api_key", "")
            settings_repo.set_setting("emailnator_email_types", '["public_gmail_plus"]')
            settings_repo.set_setting("duckmail_api_base", "https://api.duckmail.sbs")
            settings_repo.set_setting("duckmail_bearer_token", "")
            settings_repo.set_setting("tempmail_lol_api_key", "")
            settings_repo.set_setting("temp_mail_lol_api_key", "")

    def _login(self, client):
        resp = client.post("/login", json={"password": "testpass123"})
        self.assertEqual(resp.status_code, 200)

    def test_public_providers_are_registered_and_factory_discoverable(self):
        with self.app.app_context():
            from outlook_web.repositories import settings as settings_repo
            from outlook_web.services.temp_mail_provider_factory import get_available_providers, get_temp_mail_provider

            names = {item["name"] for item in get_available_providers()}

            self.assertIn("mail_tm", names)
            self.assertIn("duckmail", names)
            self.assertIn("tempmail_lol", names)
            self.assertIn("emailnator", names)
            self.assertEqual(get_temp_mail_provider("mail_tm").provider_name, "mail_tm")
            self.assertEqual(get_temp_mail_provider("duckmail").provider_name, "duckmail")
            self.assertEqual(get_temp_mail_provider("tempmail_lol").provider_name, "tempmail_lol")
            self.assertEqual(get_temp_mail_provider("emailnator").provider_name, "emailnator")
            self.assertEqual(settings_repo.validate_temp_mail_provider_name("mail_tm"), "mail_tm")
            self.assertEqual(settings_repo.validate_temp_mail_provider_name("duckmail"), "duckmail")
            self.assertEqual(settings_repo.validate_temp_mail_provider_name("tempmail_lol"), "tempmail_lol")
            self.assertEqual(settings_repo.validate_temp_mail_provider_name("emailnator"), "emailnator")

    def test_mail_tm_get_options_parses_hydra_domains(self):
        from outlook_web.services.temp_mail_provider_public import MailTmTempMailProvider

        domains_resp = _response(
            payload={
                "hydra:member": [
                    {"domain": "mail.tm", "isActive": True, "isPrivate": False},
                    {"domain": "private.tm", "isActive": True, "isPrivate": True},
                ]
            }
        )
        with patch("requests.get", return_value=domains_resp):
            options = MailTmTempMailProvider(provider_name="mail_tm").get_options()

        self.assertEqual(options["provider_name"], "mail_tm")
        self.assertEqual(options["provider_label"], "Mail.tm")
        self.assertEqual(options["domains"][0], {"name": "mail.tm", "enabled": True, "is_default": True})
        self.assertEqual(options["domains"][1]["enabled"], False)

    def test_mail_tm_api_base_can_come_from_environment(self):
        from outlook_web.services.temp_mail_provider_public import MailTmTempMailProvider

        with patch.dict("os.environ", {"MAILTM_API_BASE": "https://api.mail.tm/"}):
            provider = MailTmTempMailProvider(provider_name="mail_tm")

        self.assertEqual(provider._base_url, "https://api.mail.tm")

    def test_mail_tm_create_mailbox_stores_account_secret_and_token(self):
        from outlook_web.services.temp_mail_provider_public import MailTmTempMailProvider

        account_resp = _response(payload={"id": "account-1", "address": "demo@mail.tm"})
        token_resp = _response(payload={"id": "token-1", "token": "jwt-token"})

        with patch("requests.post", side_effect=[account_resp, token_resp]) as post_mock:
            result = MailTmTempMailProvider(provider_name="mail_tm").create_mailbox(prefix="demo", domain="mail.tm")

        self.assertTrue(result["success"])
        self.assertEqual(result["email"], "demo@mail.tm")
        self.assertEqual(result["provider_name"], "mail_tm")
        self.assertEqual(result["meta"]["provider_mailbox_id"], "account-1")
        self.assertEqual(result["meta"]["provider_jwt"], "jwt-token")
        self.assertTrue(result["meta"]["provider_secret"])

        account_payload = post_mock.call_args_list[0].kwargs["json"]
        token_payload = post_mock.call_args_list[1].kwargs["json"]
        self.assertEqual(account_payload["address"], "demo@mail.tm")
        self.assertEqual(token_payload["address"], "demo@mail.tm")
        self.assertEqual(token_payload["password"], account_payload["password"])

    def test_mail_tm_list_and_detail_normalize_messages(self):
        from outlook_web.services.temp_mail_provider_public import MailTmTempMailProvider

        mailbox = {"email": "demo@mail.tm", "meta": {"provider_jwt": "jwt-token"}}
        list_resp = _response(
            payload={
                "hydra:member": [
                    {
                        "id": "msg-1",
                        "from": {"address": "noreply@example.com"},
                        "subject": "Verify",
                        "intro": "Code 123456",
                        "createdAt": "2026-07-05T01:02:03+00:00",
                    }
                ]
            }
        )
        detail_resp = _response(
            payload={
                "id": "msg-1",
                "from": {"address": "noreply@example.com"},
                "subject": "Verify detail",
                "text": "Code 123456",
                "html": ["<p>Code <b>123456</b></p>"],
                "createdAt": "2026-07-05T01:02:03+00:00",
            }
        )

        provider = MailTmTempMailProvider(provider_name="mail_tm")
        with patch("requests.get", return_value=list_resp):
            messages = provider.list_messages(mailbox)
        with patch("requests.get", return_value=detail_resp):
            detail = provider.get_message_detail(mailbox, "mail_tm_msg-1")

        self.assertEqual(messages[0]["id"], "mail_tm_msg-1")
        self.assertEqual(messages[0]["from_address"], "noreply@example.com")
        self.assertEqual(messages[0]["timestamp"], 1783213323)
        self.assertIsNotNone(detail)
        assert detail is not None
        self.assertEqual(detail["message_id"], "mail_tm_msg-1")
        self.assertTrue(detail["has_html"])

    def test_tempmail_lol_create_and_list_normalize_messages(self):
        from outlook_web.services.temp_mail_provider_public import TempMailLolProvider

        create_resp = _response(payload={"address": "demo@public-provider.test", "token": "inbox-token"})
        inbox_resp = _response(
            payload={
                "expired": False,
                "emails": [
                    {
                        "from": "sender@example.com",
                        "to": "demo@public-provider.test",
                        "subject": "Welcome",
                        "body": "hello",
                        "html": "<p>hello</p>",
                        "date": 1783213323000,
                    }
                ],
            }
        )

        provider = TempMailLolProvider(provider_name="tempmail_lol")
        with patch("requests.post", return_value=create_resp):
            created = provider.create_mailbox(prefix="demo")
        with patch("requests.get", return_value=inbox_resp):
            messages = provider.list_messages({"email": created["email"], "meta": created["meta"]})

        self.assertTrue(created["success"])
        self.assertEqual(created["provider_name"], "tempmail_lol")
        self.assertEqual(created["meta"]["provider_jwt"], "inbox-token")
        self.assertFalse(created["meta"]["provider_capabilities"]["delete_message"])
        self.assertEqual(len(messages), 1)
        self.assertTrue(messages[0]["id"].startswith("tempmail_lol_"))
        self.assertEqual(messages[0]["timestamp"], 1783213323)
        self.assertTrue(messages[0]["has_html"])

    def test_tempmail_lol_api_key_can_come_from_environment(self):
        from outlook_web.repositories import settings as settings_repo
        from outlook_web.services.temp_mail_provider_public import TempMailLolProvider

        with self.app.app_context():
            settings_repo.set_setting("tempmail_lol_api_key", "")
            settings_repo.set_setting("temp_mail_lol_api_key", "")

        with patch.dict("os.environ", {"TEMPMAIL_LOL_API_KEY": "env-temp-key"}):
            provider = TempMailLolProvider(provider_name="tempmail_lol")

        self.assertEqual(provider._api_key, "env-temp-key")
        self.assertEqual(provider._headers()["Authorization"], "Bearer env-temp-key")

    def test_tempmail_lol_api_key_accepts_legacy_environment_alias(self):
        from outlook_web.repositories import settings as settings_repo
        from outlook_web.services.temp_mail_provider_public import TempMailLolProvider

        with self.app.app_context():
            settings_repo.set_setting("tempmail_lol_api_key", "")
            settings_repo.set_setting("temp_mail_lol_api_key", "")

        with patch.dict("os.environ", {"TEMP_MAIL_LOL_API_KEY": "legacy-env-temp-key"}):
            provider = TempMailLolProvider(provider_name="tempmail_lol")

        self.assertEqual(provider._api_key, "legacy-env-temp-key")
        self.assertEqual(provider._headers()["Authorization"], "Bearer legacy-env-temp-key")

    def test_duckmail_create_uses_configured_base_and_bearer_token(self):
        from outlook_web.services.temp_mail_provider_public import DuckMailTempMailProvider

        with self.app.app_context():
            from outlook_web.repositories import settings as settings_repo

            settings_repo.set_setting("duckmail_api_base", "https://api.duckmail.sbs")
            settings_repo.set_setting("duckmail_bearer_token", "duck-token")

        account_resp = _response(payload={"id": "duck-account", "address": "demo@duckmail.sbs"})
        token_resp = _response(payload={"id": "duck-token-id", "token": "mailbox-jwt"})

        with patch("requests.post", side_effect=[account_resp, token_resp]) as post_mock:
            result = DuckMailTempMailProvider(provider_name="duckmail").create_mailbox(prefix="demo", domain="duckmail.sbs")

        self.assertTrue(result["success"])
        self.assertEqual(result["provider_name"], "duckmail")
        self.assertEqual(result["meta"]["provider_name"], "duckmail")
        self.assertEqual(result["meta"]["provider_debug"], {"bridge": "duckmail_mail_tm"})
        self.assertEqual(post_mock.call_args_list[0].args[0], "https://api.duckmail.sbs/accounts")
        self.assertEqual(post_mock.call_args_list[0].kwargs["headers"]["Authorization"], "Bearer duck-token")
        self.assertEqual(post_mock.call_args_list[1].args[0], "https://api.duckmail.sbs/token")
        self.assertEqual(post_mock.call_args_list[1].kwargs["headers"]["Authorization"], "Bearer duck-token")

    def test_duckmail_config_can_come_from_environment(self):
        from outlook_web.repositories import settings as settings_repo
        from outlook_web.services.temp_mail_provider_public import DuckMailTempMailProvider

        with self.app.app_context():
            settings_repo.set_setting("duckmail_api_base", "")
            settings_repo.set_setting("duckmail_bearer_token", "")

        with patch.dict(
            "os.environ",
            {
                "DUCKMAIL_API_BASE": "https://api.duckmail.sbs/",
                "DUCKMAIL_BEARER_TOKEN": "env-duck-token",
            },
        ):
            provider = DuckMailTempMailProvider(provider_name="duckmail")
            self.assertEqual(provider._base_url, "https://api.duckmail.sbs")
            self.assertEqual(provider._service_bearer_token(), "env-duck-token")

    def test_duckmail_options_without_token_do_not_call_upstream_domains(self):
        from outlook_web.repositories import settings as settings_repo
        from outlook_web.services.temp_mail_provider_public import DuckMailTempMailProvider

        with self.app.app_context():
            settings_repo.set_setting("duckmail_api_base", "https://api.duckmail.sbs")
            settings_repo.set_setting("duckmail_bearer_token", "")

        with patch("requests.get") as get_mock:
            options = DuckMailTempMailProvider(provider_name="duckmail").get_options()

        get_mock.assert_not_called()
        self.assertFalse(options["configured"])
        self.assertEqual(options["missing_config"], ["duckmail_bearer_token"])
        self.assertEqual(options["provider_name"], "duckmail")

    def test_duckmail_env_base_overrides_built_in_default_setting(self):
        from outlook_web.repositories import settings as settings_repo
        from outlook_web.services.temp_mail_provider_public import DuckMailTempMailProvider

        with self.app.app_context():
            settings_repo.set_setting("duckmail_api_base", "https://api.duckmail.sbs")

        with patch.dict("os.environ", {"DUCKMAIL_API_BASE": "https://duck-env.example/"}):
            provider = DuckMailTempMailProvider(provider_name="duckmail")

        self.assertEqual(provider._base_url, "https://duck-env.example")

    def test_duckmail_explicit_db_base_takes_priority_over_environment(self):
        from outlook_web.repositories import settings as settings_repo
        from outlook_web.services.temp_mail_provider_public import DuckMailTempMailProvider

        with self.app.app_context():
            settings_repo.set_setting("duckmail_api_base", "https://duck-db.example/")

        with patch.dict("os.environ", {"DUCKMAIL_API_BASE": "https://duck-env.example/"}):
            provider = DuckMailTempMailProvider(provider_name="duckmail")

        self.assertEqual(provider._base_url, "https://duck-db.example")

    def test_duckmail_normalizes_message_ids_with_duckmail_prefix(self):
        from outlook_web.services.temp_mail_provider_public import DuckMailTempMailProvider

        with self.app.app_context():
            from outlook_web.repositories import settings as settings_repo

            settings_repo.set_setting("duckmail_api_base", "https://api.duckmail.sbs")
            settings_repo.set_setting("duckmail_bearer_token", "duck-token")

        mailbox = {"email": "demo@duckmail.sbs", "meta": {"provider_jwt": "mailbox-jwt"}}
        list_resp = _response(
            payload={
                "hydra:member": [
                    {
                        "id": "msg-1",
                        "from": {"address": "noreply@example.com"},
                        "subject": "Duck",
                        "intro": "hello",
                        "createdAt": "2026-07-05T01:02:03+00:00",
                    }
                ]
            }
        )
        detail_resp = _response(
            payload={
                "id": "msg-1",
                "from": {"address": "noreply@example.com"},
                "subject": "Duck detail",
                "text": "hello",
                "createdAt": "2026-07-05T01:02:03+00:00",
            }
        )
        delete_resp = _response(payload={})

        provider = DuckMailTempMailProvider(provider_name="duckmail")
        with patch("requests.get", return_value=list_resp) as list_mock:
            messages = provider.list_messages(mailbox)
        with patch("requests.get", return_value=detail_resp) as detail_mock:
            detail = provider.get_message_detail(mailbox, "duckmail_msg-1")
        with patch("requests.delete", return_value=delete_resp) as delete_mock:
            deleted = provider.delete_message(mailbox, "duckmail_msg-1")

        self.assertEqual(messages[0]["id"], "duckmail_msg-1")
        self.assertEqual(detail["message_id"], "duckmail_msg-1")
        self.assertTrue(deleted)
        self.assertEqual(list_mock.call_args.args[0], "https://api.duckmail.sbs/messages")
        self.assertEqual(list_mock.call_args.kwargs["headers"]["Authorization"], "Bearer mailbox-jwt")
        self.assertEqual(detail_mock.call_args.args[0], "https://api.duckmail.sbs/messages/msg-1")
        self.assertEqual(detail_mock.call_args.kwargs["headers"]["Authorization"], "Bearer mailbox-jwt")
        self.assertEqual(delete_mock.call_args.args[0], "https://api.duckmail.sbs/messages/msg-1")
        self.assertEqual(delete_mock.call_args.kwargs["headers"]["Authorization"], "Bearer mailbox-jwt")

    def test_emailnator_create_requires_api_key(self):
        from outlook_web.services.temp_mail_provider_public import EmailnatorTempMailProvider

        with self.app.app_context():
            from outlook_web.repositories import settings as settings_repo

            settings_repo.set_setting("emailnator_api_key", "")

        result = EmailnatorTempMailProvider(provider_name="emailnator").create_mailbox()

        self.assertFalse(result["success"])
        self.assertEqual(result["error_code"], "TEMP_MAIL_PROVIDER_NOT_CONFIGURED")

    def test_emailnator_config_can_come_from_environment(self):
        from outlook_web.repositories import settings as settings_repo
        from outlook_web.services.temp_mail_provider_public import EmailnatorTempMailProvider

        with self.app.app_context():
            settings_repo.set_setting("emailnator_api_key", "")
            settings_repo.set_setting("emailnator_email_types", '["public_gmail_plus"]')

        with patch.dict(
            "os.environ",
            {
                "EMAILNATOR_API_KEY": "env-rapid-key",
                "EMAILNATOR_EMAIL_TYPES": '["private_gmail_plus","private_gmail_dot"]',
            },
        ):
            provider = EmailnatorTempMailProvider(provider_name="emailnator")
            self.assertEqual(provider._api_key(), "env-rapid-key")
            self.assertEqual(provider._email_types(), ["private_gmail_plus", "private_gmail_dot"])

    def test_emailnator_explicit_db_types_take_priority_over_environment(self):
        from outlook_web.repositories import settings as settings_repo
        from outlook_web.services.temp_mail_provider_public import EmailnatorTempMailProvider

        with self.app.app_context():
            settings_repo.set_setting("emailnator_email_types", '["public_gmail_dot"]')

        with patch.dict("os.environ", {"EMAILNATOR_EMAIL_TYPES": '["private_gmail_plus"]'}):
            provider = EmailnatorTempMailProvider(provider_name="emailnator")

        self.assertEqual(provider._email_types(), ["public_gmail_dot"])

    def test_emailnator_create_and_list_detail_delete_normalize_messages(self):
        from outlook_web.services.temp_mail_provider_public import EmailnatorTempMailProvider

        with self.app.app_context():
            from outlook_web.repositories import settings as settings_repo

            settings_repo.set_setting("emailnator_api_key", "rapid-key")
            settings_repo.set_setting("emailnator_email_types", '["public_gmail_plus"]')

        create_resp = _response(payload={"status": "success", "email": "demo@gmail.com", "type": "public_gmail_plus"})
        list_resp = _response(
            payload={
                "status": "success",
                "messages": [
                    {
                        "id": "encrypted/id+1=",
                        "from": "noreply@example.com",
                        "subject": "Verify",
                        "timestamp": 1783213323,
                    }
                ],
            }
        )
        detail_resp = _response(
            payload={
                "id": "gmail-raw-id",
                "from": "noreply@example.com",
                "subject": "Verify detail",
                "timestamp": 1783213323,
                "content": "<p>Code <strong>123456</strong></p>",
                "has_attachments": False,
            }
        )
        delete_resp = _response(payload={"success": True})

        provider = EmailnatorTempMailProvider(provider_name="emailnator")
        with patch("requests.post", return_value=create_resp) as post_mock:
            created = provider.create_mailbox(prefix="ignored")
            create_payload = post_mock.call_args.kwargs["json"]
            create_headers = post_mock.call_args.kwargs["headers"]
        with patch("requests.post", return_value=list_resp) as list_mock:
            messages = provider.list_messages({"email": created["email"], "meta": created["meta"]})
        with patch("requests.get", return_value=detail_resp) as get_mock:
            detail = provider.get_message_detail({"email": created["email"], "meta": created["meta"]}, "emailnator_encrypted/id+1=")
        with patch("requests.delete", return_value=delete_resp) as delete_mock:
            deleted = provider.delete_message({"email": created["email"], "meta": created["meta"]}, "emailnator_encrypted/id+1=")

        self.assertTrue(created["success"])
        self.assertEqual(created["provider_name"], "emailnator")
        self.assertEqual(created["meta"]["provider_mailbox_id"], "demo@gmail.com")
        self.assertTrue(created["meta"]["provider_capabilities"]["delete_message"])
        self.assertEqual(create_payload, {"type": ["public_gmail_plus"]})
        self.assertEqual(create_headers["X-RapidAPI-Host"], "gmailnator.p.rapidapi.com")
        self.assertEqual(list_mock.call_args.args[0], "https://gmailnator.p.rapidapi.com/api/inbox")
        self.assertEqual(list_mock.call_args.kwargs["json"], {"email": "demo@gmail.com", "limit": 20})
        self.assertEqual(list_mock.call_args.kwargs["headers"]["X-RapidAPI-Host"], "gmailnator.p.rapidapi.com")
        self.assertEqual(messages[0]["id"], "emailnator_encrypted/id+1=")
        self.assertEqual(messages[0]["timestamp"], 1783213323)
        self.assertIsNotNone(detail)
        assert detail is not None
        self.assertEqual(detail["message_id"], "emailnator_encrypted/id+1=")
        self.assertTrue(detail["has_html"])
        self.assertIn("encrypted%2Fid%2B1%3D", get_mock.call_args.args[0])
        self.assertIn("encrypted%2Fid%2B1%3D", delete_mock.call_args.args[0])
        self.assertTrue(deleted)

    def test_emailnator_settings_api_masks_key_and_preserves_placeholder(self):
        client = self.app.test_client()
        self._login(client)

        resp = client.put(
            "/api/settings",
            json={
                "emailnator_api_key": "rapid-secret-123456",
                "emailnator_email_types": ["public_gmail_plus", "public_gmail_dot"],
            },
        )

        self.assertEqual(resp.status_code, 200)
        settings_resp = client.get("/api/settings")
        settings_payload = settings_resp.get_json()["settings"]
        masked = settings_payload["emailnator_api_key_masked"]
        self.assertTrue(settings_payload["emailnator_api_key_set"])
        self.assertNotEqual(masked, "rapid-secret-123456")
        self.assertEqual(settings_payload["emailnator_email_types"], ["public_gmail_plus", "public_gmail_dot"])

        second_resp = client.put("/api/settings", json={"emailnator_api_key": masked})

        self.assertEqual(second_resp.status_code, 200)
        with self.app.app_context():
            from outlook_web.repositories import settings as settings_repo

            self.assertEqual(settings_repo.get_emailnator_api_key(), "rapid-secret-123456")

    def test_emailnator_settings_accepts_private_email_types(self):
        client = self.app.test_client()
        self._login(client)

        resp = client.put(
            "/api/settings",
            json={"emailnator_email_types": ["private_gmail_plus", "private_gmail_dot", "private_gmail_plus"]},
        )

        self.assertEqual(resp.status_code, 200)
        settings_payload = client.get("/api/settings").get_json()["settings"]
        self.assertEqual(settings_payload["emailnator_email_types"], ["private_gmail_plus", "private_gmail_dot"])

    def test_duckmail_settings_api_masks_token_and_preserves_placeholder(self):
        client = self.app.test_client()
        self._login(client)

        resp = client.put(
            "/api/settings",
            json={
                "duckmail_api_base": "https://api.duckmail.sbs",
                "duckmail_bearer_token": "duck-secret-123456",
            },
        )

        self.assertEqual(resp.status_code, 200)
        settings_payload = client.get("/api/settings").get_json()["settings"]
        masked = settings_payload["duckmail_bearer_token_masked"]
        self.assertEqual(settings_payload["duckmail_api_base"], "https://api.duckmail.sbs")
        self.assertTrue(settings_payload["duckmail_bearer_token_set"])
        self.assertNotEqual(masked, "duck-secret-123456")

        second_resp = client.put("/api/settings", json={"duckmail_bearer_token": masked})

        self.assertEqual(second_resp.status_code, 200)
        with self.app.app_context():
            from outlook_web.repositories import settings as settings_repo

            self.assertEqual(settings_repo.get_duckmail_bearer_token(), "duck-secret-123456")

    def test_tempmail_lol_settings_api_masks_key_and_preserves_placeholder(self):
        client = self.app.test_client()
        self._login(client)

        resp = client.put("/api/settings", json={"tempmail_lol_api_key": "temp-lol-secret-123456"})

        self.assertEqual(resp.status_code, 200)
        settings_payload = client.get("/api/settings").get_json()["settings"]
        masked = settings_payload["tempmail_lol_api_key_masked"]
        self.assertTrue(settings_payload["tempmail_lol_api_key_set"])
        self.assertNotEqual(masked, "temp-lol-secret-123456")

        second_resp = client.put("/api/settings", json={"tempmail_lol_api_key": masked})

        self.assertEqual(second_resp.status_code, 200)
        with self.app.app_context():
            from outlook_web.repositories import settings as settings_repo

            self.assertEqual(settings_repo.get_tempmail_lol_api_key(), "temp-lol-secret-123456")

    def test_provider_secret_survives_temp_mailbox_meta_serialization(self):
        with self.app.app_context():
            from outlook_web.repositories import temp_emails as temp_emails_repo

            temp_emails_repo.create_temp_email(
                email_addr="secret@public-provider.test",
                source="custom_domain_temp_mail",
                provider_name="mail_tm",
                meta={
                    "provider_name": "mail_tm",
                    "provider_mailbox_id": "account-1",
                    "provider_jwt": "jwt-token",
                    "provider_secret": "account-password",
                    "provider_capabilities": {"delete_mailbox": True, "delete_message": True, "clear_messages": True},
                },
            )
            descriptor = temp_emails_repo.get_temp_email_by_address("secret@public-provider.test", view="descriptor")

        self.assertEqual(descriptor["provider_name"], "mail_tm")
        self.assertEqual(descriptor["meta"]["provider_secret"], "account-password")

    def test_local_delete_skips_provider_when_capability_is_false(self):
        with self.app.app_context():
            from outlook_web.db import get_db
            from outlook_web.repositories import temp_emails as temp_emails_repo
            from outlook_web.services.temp_mail_service import TempMailService

            temp_emails_repo.create_temp_email(
                email_addr="local-delete@public-provider.test",
                source="custom_domain_temp_mail",
                provider_name="tempmail_lol",
                meta={
                    "provider_name": "tempmail_lol",
                    "provider_capabilities": {"delete_mailbox": False, "delete_message": False, "clear_messages": False},
                },
            )
            db = get_db()
            db.execute(
                """
                INSERT INTO temp_email_messages
                (message_id, email_address, from_address, subject, content, html_content, has_html, timestamp, raw_content)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                ("msg-local", "local-delete@public-provider.test", "a@example.com", "s", "c", "", 0, 1, "{}"),
            )
            db.commit()

            def fail_provider_factory(provider_name=None):
                raise AssertionError("provider should not be initialized for local-only delete")

            service = TempMailService(provider_factory=fail_provider_factory)
            service.delete_message("local-delete@public-provider.test", "msg-local")
            remaining = temp_emails_repo.get_temp_email_message_by_id("msg-local", email_addr="local-delete@public-provider.test")

        self.assertIsNone(remaining)

    def test_api_options_support_public_provider_names(self):
        client = self.app.test_client()
        self._login(client)

        domains_resp = _response(payload={"hydra:member": [{"domain": "mail.tm", "isActive": True}]})
        with patch("requests.get", return_value=domains_resp):
            mail_tm_resp = client.get("/api/temp-emails/options?provider_name=mail_tm")
            duckmail_resp = client.get("/api/temp-emails/options?provider_name=duckmail")
        tempmail_lol_resp = client.get("/api/temp-emails/options?provider_name=tempmail_lol")
        emailnator_resp = client.get("/api/temp-emails/options?provider_name=emailnator")

        self.assertEqual(mail_tm_resp.status_code, 200)
        self.assertEqual(mail_tm_resp.get_json()["options"]["provider_name"], "mail_tm")
        self.assertEqual(duckmail_resp.status_code, 200)
        self.assertEqual(duckmail_resp.get_json()["options"]["provider_name"], "duckmail")
        self.assertTrue(duckmail_resp.get_json()["options"]["requires_bearer_token"])
        self.assertEqual(tempmail_lol_resp.status_code, 200)
        self.assertEqual(tempmail_lol_resp.get_json()["options"]["provider_name"], "tempmail_lol")
        self.assertEqual(emailnator_resp.status_code, 200)
        self.assertEqual(emailnator_resp.get_json()["options"]["provider_name"], "emailnator")
        self.assertTrue(emailnator_resp.get_json()["options"]["requires_api_key"])


if __name__ == "__main__":
    unittest.main()
