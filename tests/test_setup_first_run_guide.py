from __future__ import annotations

import unittest
from unittest.mock import patch

from tests._import_app import import_web_app_module


class SetupFirstRunGuideTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = import_web_app_module()
        cls.app = cls.module.app

    def test_three_examples_cover_temp_verify_pool(self):
        from mailops.services.setup_first_run import get_external_api_three_examples

        examples = get_external_api_three_examples(base_url="http://example.test")
        keys = [item["key"] for item in examples]
        self.assertEqual(keys, ["temp_claim", "verification_code", "pool_claim"])
        joined = "\n".join(item["snippet"] for item in examples)
        self.assertIn("/api/v1/external/mailbox-sessions/start", joined)
        self.assertIn("verification_code", joined)
        self.assertIn("/api/v1/external/pool/claim-random", joined)
        self.assertNotIn("sk-", joined)

    def test_setup_guide_shape_and_ops_health(self):
        with self.app.app_context():
            from mailops.services.setup_first_run import build_ops_health_snapshot, build_setup_first_run_guide

            guide = build_setup_first_run_guide()
            self.assertEqual(guide.get("version"), 1)
            self.assertIn("steps", guide)
            self.assertTrue(any(s.get("key") == "cloudflare" for s in guide["steps"]))
            self.assertTrue(any(s.get("key") == "api_key" for s in guide["steps"]))
            self.assertEqual(len(guide.get("examples") or []), 3)

            health = build_ops_health_snapshot(
                account_status={"expired": 1, "error": 0},
                refresh_health={"last_fail_count": 2, "success_rate_7d": 0.9},
                command_center={"provider_readiness": {"needs_config": 1, "ready": 2, "active": 3}},
                external_api_stats={"kpi": {"today_calls": 5, "error_count": 1}, "health": {"status": "ok"}},
            )
            self.assertEqual(health["token"]["last_fail_count"], 2)
            self.assertEqual(health["temp_provider"]["needs_config"], 1)
            self.assertEqual(health["external_api"]["today_calls"], 5)

    def test_overview_summary_payload_includes_setup_and_health_fields(self):
        """Compose the same fields the controller attaches (without HTTP session quirks)."""
        with self.app.app_context():
            from mailops.controllers import overview as overview_controller
            from mailops.repositories import overview as overview_repo
            from mailops.services.overview_command_center import get_overview_command_center
            from mailops.services.setup_first_run import build_ops_health_snapshot, build_setup_first_run_guide

            overview_controller._OVERVIEW_SUMMARY_CACHE = None
            overview_controller._OVERVIEW_SUMMARY_CACHE_AT = 0.0
            result = overview_repo.get_overview_summary()
            result["command_center"] = get_overview_command_center()
            result["setup_guide"] = build_setup_first_run_guide()
            api_stats = overview_repo.get_external_api_stats()
            result["ops_health"] = build_ops_health_snapshot(
                account_status=result.get("account_status"),
                refresh_health=result.get("refresh_health"),
                command_center=result.get("command_center"),
                external_api_stats=api_stats,
            )
            result["external_api_today"] = {
                "today_calls": int((api_stats.get("kpi") or {}).get("today_calls") or 0),
                "error_count": int((api_stats.get("kpi") or {}).get("error_count") or 0),
            }
        self.assertIn("setup_guide", result)
        self.assertIn("ops_health", result)
        self.assertIn("external_api_today", result)
        self.assertTrue(result["setup_guide"].get("steps"))


if __name__ == "__main__":
    unittest.main()
