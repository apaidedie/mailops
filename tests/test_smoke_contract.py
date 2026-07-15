from __future__ import annotations

from tests.frontend_js_bundle import load_frontend_app_js
import unittest

from tests._import_app import clear_login_attempts, import_web_app_module


class SmokeContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = import_web_app_module()
        cls.app = cls.module.app

    def setUp(self):
        # 每个测试前清理登录限制记录，避免测试间互相影响
        with self.app.app_context():
            clear_login_attempts()

    def _login(self, client):
        resp = client.post("/login", json={"password": "testpass123"})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data.get("success"), True)

    def test_healthz_contract(self):
        client = self.app.test_client()
        resp = client.get("/healthz")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data.get("status"), "ok")
        # 新增字段：用于前端判断是否发生重启
        self.assertTrue(data.get("boot_id"))
        self.assertTrue(data.get("version"))

    def test_pages_are_accessible(self):
        client = self.app.test_client()

        # 登录页（未登录也可访问）
        resp = client.get("/login")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/html", (resp.headers.get("Content-Type") or ""))

        # 主页（需要登录）
        self._login(client)
        resp = client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/html", (resp.headers.get("Content-Type") or ""))
        html = resp.get_data(as_text=True)
        # 前端静态资源应已迁出（零构建）：不再内联 style/script
        self.assertNotIn("<style>", html)
        self.assertNotIn("<script>", html)
        self.assertIn("css/main.css", html)
        self.assertIn("js/core/state/globals.js", html)
        self.assertIn("js/features/groups/globals.js", html)
        self.assertIn("js/features/accounts/globals.js", html)
        self.assertIn("js/features/mailbox_compact.js", html)
        self.assertNotIn("js/layout-manager.js", html)
        self.assertNotIn("js/layout-bootstrap.js", html)
        self.assertNotIn("js/state-manager.js", html)
        self.assertNotIn("css/layout.css", html)
        self.assertIn('id="toast-container"', html)
        self.assertNotIn('id="toast"', html)

    def test_static_asset_is_accessible(self):
        client = self.app.test_client()
        resp = client.get("/static/health.txt")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("ok", resp.get_data(as_text=True))
        resp.close()

        # 新增静态资源（P0-5）：CSS/JS 迁出与拆分
        resp = client.get("/static/css/main.css")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(".navbar", resp.get_data(as_text=True))
        resp.close()

        main_js = load_frontend_app_js()
        self.assertIn("initCSRFToken", main_js)
        # Soft joins any in-flight CSRF pull; force joins only force and supersedes soft
        # so CSRF_TOKEN_INVALID recovery always starts a true /api/csrf-token GET.
        self.assertIn("let csrfTokenRefreshForce = false", main_js)
        self.assertIn("if (!force || csrfTokenRefreshForce)", main_js)
        self.assertIn("csrfTokenRefreshForce = Boolean(force)", main_js)
        self.assertIn("csrfTokenRefreshPromise !== request", main_js)
        self.assertIn("initCSRFToken({ force: true, silent: true })", main_js)
        resp = client.get("/static/js/core/http.js")
        self.assertEqual(resp.status_code, 200)
        resp.close()

        resp = client.get("/static/js/features/groups/globals.js")
        self.assertEqual(resp.status_code, 200)
        resp.close()
        from tests.frontend_js_bundle import load_feature_package_js

        self.assertIn("loadGroups", load_feature_package_js("static/js/features/groups"))

        resp = client.get("/static/js/features/mailbox_compact.js")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("switchMailboxViewMode", resp.get_data(as_text=True))
        resp.close()

    def test_contract_sampled_endpoints_after_login(self):
        client = self.app.test_client()
        self._login(client)

        resp = client.get("/api/system/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data.get("success"), True)
        health = data.get("health") or {}
        self.assertIn("service", health)
        self.assertIn("database", health)
        self.assertIn("scheduler", health)
        self.assertIn("refresh", health)

        resp = client.get("/api/scheduler/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data.get("success"), True)
        self.assertIn("scheduler", data)
        self.assertIn("refresh", data)

        resp = client.get("/api/system/upgrade-status")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data.get("success"), True)
        upgrade = data.get("upgrade") or {}
        self.assertIn("schema_version", upgrade)
        self.assertIn("target_version", upgrade)
        self.assertIn("up_to_date", upgrade)
        self.assertIn("backup_hint", upgrade)

        resp = client.get("/api/groups")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data.get("success"), True)
        self.assertIsInstance(data.get("groups"), list)

        resp = client.get("/api/tags")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data.get("success"), True)
        self.assertIsInstance(data.get("tags"), list)

        resp = client.get("/api/accounts")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data.get("success"), True)
        self.assertIsInstance(data.get("accounts"), list)

        resp = client.get("/api/mailboxes")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data.get("success"), True)
        self.assertIsInstance(data.get("mailboxes"), list)
        self.assertIn("contract", data)

        resp = client.get("/api/audit-logs")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data.get("success"), True)
        self.assertIsInstance(data.get("logs"), list)
        self.assertIn("total", data)
        self.assertIn("limit", data)
        self.assertIn("offset", data)
