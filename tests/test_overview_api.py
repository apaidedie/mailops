from __future__ import annotations

"""
TDD D 层：Overview API 接口测试

覆盖 docs/TDD/2026-04-19-数据概览大盘TDD.md §8
当前运行会失败（红）—— /api/overview/* 接口尚未注册（404）。
实现 Blueprint + 5 个接口后，所有用例应通过（绿）。
"""

import json
import unittest
from unittest.mock import patch

from tests._import_app import import_web_app_module


class OverviewApiBaseTests(unittest.TestCase):
    """基础: client 创建 + 登录获取 session"""

    @classmethod
    def setUpClass(cls):
        cls.module = import_web_app_module()
        cls.app = cls.module.app
        cls.client = cls.app.test_client()
        cls.session_cookie = cls._login(cls.client)

    @staticmethod
    def _login(client) -> str:
        resp = client.post(
            "/login",
            json={"password": "testpass123"},
            content_type="application/json",
        )
        if resp.status_code != 200:
            raise RuntimeError(f"测试用户登录失败 ({resp.status_code}): {resp.data[:200]}")
        return "loggedin"

    def _get(self, url: str, *, authed: bool = True):
        headers = {}
        if authed:
            headers["Cookie"] = self.session_cookie
        return self.client.get(url, headers=headers)

    def _assert_json(self, resp) -> dict:
        self.assertEqual(resp.content_type, "application/json", f"非 JSON 响应: {resp.data[:200]}")
        return json.loads(resp.data)

    def setUp(self):
        with self.app.app_context():
            from outlook_web.controllers import overview as overview_controller
            from outlook_web.db import get_db

            overview_controller._OVERVIEW_SUMMARY_CACHE = None
            overview_controller._OVERVIEW_SUMMARY_CACHE_AT = 0.0
            db = get_db()
            db.execute("DELETE FROM verification_extract_logs")
            db.commit()


# ===== A-01: GET /api/overview/summary =====


class OverviewSummaryApiTests(OverviewApiBaseTests):

    _URL = "/api/overview/summary"

    def test_get_summary_unauthorized_returns_401(self):
        """A-01 鉴权: 未登录时返回 401"""
        resp = self.client.get(self._URL)
        self.assertEqual(resp.status_code, 401)

    def test_get_summary_authed_returns_200(self):
        """A-01 成功: 已登录时返回 200"""
        resp = self._get(self._URL)
        self.assertEqual(resp.status_code, 200)

    def test_get_summary_response_has_required_top_level_keys(self):
        """A-01 Schema: 响应包含 account_status / pool_snapshot / refresh_health / kpi"""
        resp = self._get(self._URL)
        data = self._assert_json(resp)
        for key in ("account_status", "pool_snapshot", "refresh_health", "kpi"):
            self.assertIn(key, data, f"响应缺少顶层键: {key}")

    def test_get_summary_values_are_numeric(self):
        """A-01 数据类型: account_status 各值为整数"""
        resp = self._get(self._URL)
        data = self._assert_json(resp)
        for k, v in data.get("account_status", {}).items():
            self.assertIsInstance(v, (int, float), f"account_status.{k} 应为数值, 实际: {type(v)}")

    def test_get_summary_includes_command_center_contract(self):
        """A-01 Schema: 总览包含统一邮箱指挥台聚合状态"""
        resp = self._get(self._URL)
        data = self._assert_json(resp)
        command_center = data.get("command_center")
        self.assertIsInstance(command_center, dict)
        for key in ("overall_status", "mailbox_inventory", "provider_readiness", "external_api", "actions"):
            self.assertIn(key, command_center, f"command_center 缺少键: {key}")

        inventory = command_center["mailbox_inventory"]
        for key in ("status", "total", "account", "temp", "providers"):
            self.assertIn(key, inventory)

        provider = command_center["provider_readiness"]
        for key in ("status", "ready", "active", "needs_config", "dynamic_create", "temp_providers", "account_providers"):
            self.assertIn(key, provider)

        external_api = command_center["external_api"]
        for key in (
            "status",
            "discovery_status",
            "mailbox_directory_status",
            "task_temp_mailbox_status",
            "pool_status",
            "integration_bundle_endpoint",
        ):
            self.assertIn(key, external_api)
        self.assertEqual(external_api["integration_bundle_endpoint"], "/api/v1/external/integration-bundle")
        self.assertIsInstance(command_center["actions"], list)

    def test_get_summary_command_center_is_secret_safe(self):
        """A-01 Safety: 指挥台 payload 不暴露 token/key/bearer 等敏感字段或值"""
        resp = self._get(self._URL)
        data = self._assert_json(resp)
        serialized = json.dumps(data.get("command_center"), ensure_ascii=False).lower()
        forbidden = [
            "api_key",
            "bearer",
            "token",
            "password",
            "refresh_token",
            "claim_token",
            "task_token",
            "consumer_key",
            "authorization",
            "dk_",
        ]
        for token in forbidden:
            self.assertNotIn(token, serialized)

    def test_get_summary_command_center_degrades_when_projection_fails(self):
        """A-01 Fallback: 指挥台聚合失败时不影响 summary 接口返回"""
        from outlook_web.controllers import overview as overview_controller

        overview_controller._OVERVIEW_SUMMARY_CACHE = None
        overview_controller._OVERVIEW_SUMMARY_CACHE_AT = 0.0
        with patch("outlook_web.controllers.overview.get_overview_command_center", side_effect=RuntimeError("boom")):
            resp = self._get(self._URL)

        self.assertEqual(resp.status_code, 200)
        data = self._assert_json(resp)
        self.assertIn("account_status", data)
        self.assertEqual(data.get("command_center", {}).get("overall_status"), "degraded")


# ===== A-02: GET /api/overview/verification =====


class OverviewVerificationApiTests(OverviewApiBaseTests):

    _URL = "/api/overview/verification"

    def test_get_verification_unauthorized_returns_401(self):
        """A-02 鉴权: 未登录时返回 401"""
        resp = self.client.get(self._URL)
        self.assertEqual(resp.status_code, 401)

    def test_get_verification_authed_returns_200(self):
        """A-02 成功: 已登录时返回 200"""
        resp = self._get(self._URL)
        self.assertEqual(resp.status_code, 200)

    def test_get_verification_response_has_kpi_key(self):
        """A-02 Schema: 响应包含 kpi 字段"""
        resp = self._get(self._URL)
        data = self._assert_json(resp)
        self.assertIn("kpi", data)

    def test_get_verification_kpi_has_expected_keys(self):
        """A-02 Schema: kpi 包含 total_count / success_count / success_rate / avg_duration_ms"""
        resp = self._get(self._URL)
        data = self._assert_json(resp)
        kpi = data.get("kpi", {})
        for key in ("total_count", "success_count", "success_rate", "avg_duration_ms"):
            self.assertIn(key, kpi, f"kpi 缺少键: {key}")

    def test_get_verification_empty_data_returns_zero_counts(self):
        """A-02 空数据: 无日志时 kpi.total_count 为 0，recent 为空数组"""
        resp = self._get(self._URL)
        data = self._assert_json(resp)
        self.assertEqual(data.get("kpi", {}).get("total_count"), 0)
        self.assertEqual(data.get("recent", ["x"]), [])


# ===== A-03: GET /api/overview/external-api =====


class OverviewExternalApiTests(OverviewApiBaseTests):

    _URL = "/api/overview/external-api"

    def test_get_external_api_unauthorized_returns_401(self):
        """A-03 鉴权: 未登录时返回 401"""
        resp = self.client.get(self._URL)
        self.assertEqual(resp.status_code, 401)

    def test_get_external_api_authed_returns_200(self):
        """A-03 成功: 已登录时返回 200"""
        resp = self._get(self._URL)
        self.assertEqual(resp.status_code, 200)

    def test_get_external_api_response_schema(self):
        """A-03 Schema: 响应包含 kpi / daily_series / caller_rank"""
        resp = self._get(self._URL)
        data = self._assert_json(resp)
        for key in ("kpi", "daily_series", "caller_rank", "by_endpoint", "endpoint_health", "health"):
            self.assertIn(key, data, f"响应缺少顶层键: {key}")
        self.assertIn("error_rate", data.get("kpi", {}))

    def test_get_external_api_daily_series_is_list(self):
        """A-03: daily_series 是列表"""
        resp = self._get(self._URL)
        data = self._assert_json(resp)
        self.assertIsInstance(data.get("daily_series"), list)

    def test_get_external_api_enriched_schema_reflects_usage(self):
        """A-03 运维 Schema: 返回接口健康和调用方错误维度。"""
        with self.app.app_context():
            from datetime import date

            from outlook_web.db import get_db

            db = get_db()
            today = date.today().isoformat()
            db.execute("DELETE FROM external_api_consumer_usage_daily WHERE consumer_key='api-ops-key'")
            db.execute(
                """
                INSERT INTO external_api_consumer_usage_daily
                    (consumer_key, consumer_name, caller_id, usage_date, date, endpoint,
                     total_count, call_count, success_count, error_count, last_status, last_used_at)
                VALUES
                    ('api-ops-key', 'QA Runner', 'qa-runner', ?, ?, '/api/v1/external/messages',
                     12, 12, 9, 3, 'error', '2026-07-10T09:00:00Z')
                """,
                (today, today),
            )
            db.commit()

        try:
            resp = self._get(self._URL)
            self.assertEqual(resp.status_code, 200)
            data = self._assert_json(resp)

            self.assertEqual(data.get("health", {}).get("status"), "attention")
            self.assertEqual(data.get("endpoint_health", [])[0].get("error_count"), 3)
            self.assertEqual(data.get("caller_rank", [])[0].get("last_status"), "error")
            self.assertIn("endpoint_count", data.get("caller_rank", [])[0])
        finally:
            with self.app.app_context():
                from outlook_web.db import get_db

                db = get_db()
                db.execute("DELETE FROM external_api_consumer_usage_daily WHERE consumer_key='api-ops-key'")
                db.commit()


# ===== A-04: GET /api/overview/pool =====


class OverviewPoolApiTests(OverviewApiBaseTests):

    _URL = "/api/overview/pool"

    def test_get_pool_unauthorized_returns_401(self):
        """A-04 鉴权: 未登录时返回 401"""
        resp = self.client.get(self._URL)
        self.assertEqual(resp.status_code, 401)

    def test_get_pool_authed_returns_200(self):
        """A-04 成功: 已登录时返回 200"""
        resp = self._get(self._URL)
        self.assertEqual(resp.status_code, 200)

    def test_get_pool_response_schema(self):
        """A-04 Schema: 响应包含 kpi / recent_operations / project_top5 / operation_distribution"""
        resp = self._get(self._URL)
        data = self._assert_json(resp)
        for key in ("kpi", "recent_operations", "project_top5", "operation_distribution"):
            self.assertIn(key, data, f"响应缺少顶层键: {key}")


# ===== A-05: GET /api/overview/activity =====


class OverviewActivityApiTests(OverviewApiBaseTests):

    _URL = "/api/overview/activity"

    def test_get_activity_unauthorized_returns_401(self):
        """A-05 鉴权: 未登录时返回 401"""
        resp = self.client.get(self._URL)
        self.assertEqual(resp.status_code, 401)

    def test_get_activity_authed_returns_200(self):
        """A-05 成功: 已登录时返回 200"""
        resp = self._get(self._URL)
        self.assertEqual(resp.status_code, 200)

    def test_get_activity_response_schema(self):
        """A-05 Schema: 响应包含 kpi / timeline / notification_stats"""
        resp = self._get(self._URL)
        data = self._assert_json(resp)
        for key in ("kpi", "timeline", "notification_stats"):
            self.assertIn(key, data, f"响应缺少顶层键: {key}")

    def test_get_activity_timeline_is_list(self):
        """A-05: timeline 是列表"""
        resp = self._get(self._URL)
        data = self._assert_json(resp)
        self.assertIsInstance(data.get("timeline"), list)

    def test_get_activity_empty_returns_zero_kpi(self):
        """A-05 空数据: audit_ops_24h 为整数"""
        resp = self._get(self._URL)
        data = self._assert_json(resp)
        kpi = data.get("kpi", {})
        self.assertIsInstance(kpi.get("audit_ops_24h"), int)
