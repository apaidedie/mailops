from __future__ import annotations

import unittest


class TempMailProviderContractValidationTests(unittest.TestCase):
    def test_valid_provider_contract_has_no_issues(self):
        from mailops.services.temp_mail_provider_base import TempMailProviderBase
        from mailops.services.temp_mail_provider_contract import validate_temp_mail_provider_class

        class ValidProvider(TempMailProviderBase):
            provider_name = "valid_contract"
            provider_label = "Valid Contract"
            provider_version = "1.2.3"
            provider_author = "Tests"
            provider_capabilities = {"delete_mailbox": True, "delete_message": False, "clear_messages": True}
            config_schema = {
                "fields": [
                    {"key": "base_url", "label": "Base URL", "type": "url", "required": True, "default": "https://valid.test"},
                    {"key": "api_key", "label": "API Key", "type": "password", "required": True},
                ]
            }

            def __init__(self, *, provider_name=None):
                self.provider_name = provider_name or self.provider_name

            def get_options(self):
                return {"domains": [{"name": "valid.test"}], "provider_name": self.provider_name}

            def create_mailbox(self, *, prefix=None, domain=None):
                return {"success": True, "email": "demo@valid.test"}

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

        validation = validate_temp_mail_provider_class("valid_contract", ValidProvider, probe_options=True)

        self.assertTrue(validation["valid"])
        self.assertEqual(validation["status"], "valid")
        self.assertEqual(validation["issues"], [])
        self.assertEqual(validation["summary"]["errors"], 0)
        self.assertEqual(validation["safe_metadata"]["capabilities"]["delete_mailbox"], True)
        self.assertEqual(validation["safe_metadata"]["config_fields"][1]["secret"], True)
        self.assertTrue(validation["safe_metadata"]["options_probe"]["ok"])
        self.assertEqual(validation["safe_metadata"]["options_probe"]["domain_count"], 1)
        self.assertNotIn("api_key_value", str(validation))

    def test_invalid_metadata_returns_structured_issues(self):
        from mailops.services.temp_mail_provider_contract import validate_temp_mail_provider_class

        class InvalidProvider:
            provider_name = "wrong_name"
            provider_label = ""
            provider_version = ""
            config_schema = {"fields": [{"key": "", "type": "strange"}]}

            def get_options(self):
                return []

        validation = validate_temp_mail_provider_class("expected_name", InvalidProvider, probe_options=True)
        codes = {issue["code"] for issue in validation["issues"]}

        self.assertFalse(validation["valid"])
        self.assertEqual(validation["status"], "invalid")
        self.assertIn("PROVIDER_NAME_MISMATCH", codes)
        self.assertIn("PROVIDER_VERSION_MISSING", codes)
        self.assertIn("CONFIG_FIELD_KEY_MISSING", codes)
        self.assertIn("CONFIG_FIELD_TYPE_UNKNOWN", codes)
        self.assertIn("METHOD_NOT_IMPLEMENTED", codes)
        self.assertIn("OPTIONS_RETURN_INVALID", codes)
        self.assertIn("PROVIDER_BASE_CLASS_INVALID", codes)

    def test_non_base_provider_with_matching_methods_is_invalid(self):
        from mailops.services.temp_mail_provider_contract import (
            contract_validation_summary,
            validate_temp_mail_provider_class,
        )

        class MethodOnlyProvider:
            provider_name = "method_only"
            provider_label = "Method Only"
            provider_version = "1.0.0"
            provider_capabilities = {"delete_mailbox": True, "delete_message": True, "clear_messages": True}
            config_schema = {"fields": [{"key": "base_url", "label": "Base URL", "type": "url"}]}

            def get_options(self):
                return {"domains": []}

            def create_mailbox(self, *, prefix=None, domain=None):
                return {"success": True, "email": "demo@method.test"}

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

        validation = validate_temp_mail_provider_class("method_only", MethodOnlyProvider, probe_options=True)
        codes = {issue["code"] for issue in validation["issues"]}
        checks = {check["key"]: check for check in validation["checks"]}

        self.assertFalse(validation["valid"])
        self.assertEqual(validation["status"], "invalid")
        self.assertIn("PROVIDER_BASE_CLASS_INVALID", codes)
        self.assertFalse(checks["base_class"]["ok"])
        self.assertTrue(validation["safe_metadata"]["options_probe"]["ok"])

        summary = contract_validation_summary(validation)
        self.assertFalse(summary["valid"])
        self.assertEqual(summary["status"], "invalid")
        self.assertIn("PROVIDER_BASE_CLASS_INVALID", summary["issue_codes"])

    def test_secret_config_defaults_are_flagged_and_redacted(self):
        from mailops.services.temp_mail_provider_base import TempMailProviderBase
        from mailops.services.temp_mail_provider_contract import validate_temp_mail_provider_class

        class SecretDefaultProvider(TempMailProviderBase):
            provider_name = "secret_default"
            provider_label = "Secret Default"
            provider_version = "1.0.0"
            config_schema = {
                "fields": [
                    {
                        "key": "api_key",
                        "label": "API Key",
                        "type": "password",
                        "required": True,
                        "default": "sk-should-not-leak",
                    },
                ]
            }

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

        validation = validate_temp_mail_provider_class("secret_default", SecretDefaultProvider)
        codes = {issue["code"] for issue in validation["issues"]}

        self.assertFalse(validation["valid"])
        self.assertIn("CONFIG_FIELD_SECRET_DEFAULT", codes)
        self.assertNotIn("sk-should-not-leak", str(validation))
        field = validation["safe_metadata"]["config_fields"][0]
        self.assertTrue(field["secret"])
        self.assertNotIn("default", field)

    def test_provider_info_validation_counts_config_schema_issues(self):
        from mailops.services.temp_mail_provider_contract import validate_temp_mail_provider_info

        validation = validate_temp_mail_provider_info(
            {
                "name": "info_provider",
                "label": "Info Provider",
                "version": "1.0.0",
                "config_schema": {
                    "fields": [
                        {
                            "key": "bearer_token",
                            "label": "Bearer Token",
                            "type": "password",
                            "default": "token-should-not-leak",
                        }
                    ]
                },
            }
        )

        self.assertFalse(validation["valid"])
        self.assertEqual(validation["status"], "invalid")
        self.assertEqual(validation["summary"]["errors"], 1)
        self.assertIn("CONFIG_FIELD_SECRET_DEFAULT", {issue["code"] for issue in validation["issues"]})
        self.assertNotIn("token-should-not-leak", str(validation))


if __name__ == "__main__":
    unittest.main()
