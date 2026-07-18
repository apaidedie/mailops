import unittest
from unittest.mock import patch

from mailops.repositories.settings import normalize_temp_mail_api_base_url
from mailops.services import gptmail
from mailops.services.temp_mail_provider_custom import CustomTempMailProvider


class GptmailUsageAndBaseUrlTests(unittest.TestCase):
    def test_normalize_strips_locale_docs_path(self):
        self.assertEqual(
            normalize_temp_mail_api_base_url("https://mail.chatgpt.org.uk/zh"),
            "https://mail.chatgpt.org.uk",
        )
        self.assertEqual(
            normalize_temp_mail_api_base_url("https://mail.chatgpt.org.uk/zh/api"),
            "https://mail.chatgpt.org.uk",
        )
        self.assertEqual(
            normalize_temp_mail_api_base_url("https://mail.chatgpt.org.uk/"),
            "https://mail.chatgpt.org.uk",
        )

    def test_extract_usage_payload_keeps_int_counters(self):
        usage = gptmail.extract_usage_payload(
            {
                "success": True,
                "usage": {
                    "daily_limit": 200000,
                    "used_today": "12",
                    "remaining_today": 199988,
                    "bad": "x",
                },
            }
        )
        self.assertEqual(
            usage,
            {
                "daily_limit": 200000,
                "used_today": 12,
                "remaining_today": 199988,
            },
        )

    def test_gptmail_request_remembers_usage_from_success_payload(self):
        gptmail._LAST_USAGE.clear()

        class _Resp:
            status_code = 200

            def json(self):
                return {
                    "success": True,
                    "data": {"ok": True},
                    "usage": {
                        "daily_limit": 100,
                        "used_today": 3,
                        "remaining_today": 97,
                        "total_limit": 1000,
                        "total_usage": 30,
                        "remaining_total": 970,
                    },
                }

        with patch("mailops.services.gptmail.get_gptmail_api_key", return_value="PUBLIC_API_KEY"):
            with patch("mailops.services.gptmail.get_temp_mail_api_base_url", return_value="https://mail.chatgpt.org.uk"):
                with patch("mailops.services.gptmail.requests.get", return_value=_Resp()):
                    result = gptmail.gptmail_request("GET", "/api/stats")
        self.assertTrue(result.get("success"))
        self.assertEqual(gptmail.get_last_usage().get("remaining_today"), 97)

    def test_custom_provider_health_check_surfaces_usage(self):
        provider = CustomTempMailProvider(provider_name="legacy_bridge")
        with patch.object(
            provider,
            "get_options",
            return_value={
                "configured": True,
                "missing_config": [],
                "domains": [],
                "api_base_url": "https://mail.chatgpt.org.uk",
            },
        ):
            with patch(
                "mailops.services.gptmail.fetch_usage_stats",
                return_value={
                    "success": True,
                    "api_base_url": "https://mail.chatgpt.org.uk",
                    "usage": {
                        "daily_limit": 200000,
                        "used_today": 1,
                        "remaining_today": 199999,
                    },
                    "data": {},
                },
            ):
                result = provider.health_check()
        self.assertTrue(result.get("success"))
        self.assertEqual(result.get("method"), "stats")
        self.assertEqual(result["details"]["usage"]["remaining_today"], 199999)


if __name__ == "__main__":
    unittest.main()
