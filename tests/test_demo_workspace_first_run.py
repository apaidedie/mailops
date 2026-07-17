from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from tests._import_app import import_web_app_module
from tests.frontend_js_bundle import load_frontend_app_js


class DemoWorkspaceBootstrapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = import_web_app_module()
        cls.app = cls.module.app
        cls.repo_root = Path(__file__).resolve().parents[1]

    def _login(self, client, password: str = "testpass123") -> None:
        with client.session_transaction() as session:
            session["logged_in"] = True
            session["user_id"] = "demo-workspace-test"

    def _bootstrap_payload(self, *, configured_database_path: Path) -> dict:
        """Load bootstrap while only overriding demo-path resolution.

        Do not rewrite DATABASE_PATH env: settings still need the isolated test DB.
        """
        client = self.app.test_client()
        self._login(client)
        with patch(
            "outlook_web.controllers.system.helpers._resolve_configured_database_path",
            return_value=configured_database_path.resolve(strict=False),
        ):
            resp = client.get("/api/bootstrap")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json() or {}
        self.assertTrue(data.get("success"))
        return data.get("bootstrap") or {}

    def test_bootstrap_marks_default_local_demo_database(self):
        demo_path = self.repo_root / "output" / "demo" / "outlook-email-plus-demo.db"
        bootstrap = self._bootstrap_payload(configured_database_path=demo_path)
        demo = bootstrap.get("demo_workspace") or {}

        self.assertTrue(demo.get("enabled"))
        self.assertEqual(demo.get("database"), "output/demo/outlook-email-plus-demo.db")
        self.assertTrue(demo.get("synthetic"))

        actions = {item.get("key"): item for item in demo.get("quick_actions") or []}
        for key in ["overview", "unified_mailbox", "temp_mailboxes", "external_api", "providers"]:
            self.assertIn(key, actions)
        self.assertEqual(actions["external_api"].get("page"), "dashboard")
        self.assertEqual(actions["external_api"].get("tab"), "external-api")
        self.assertEqual(actions["providers"].get("tab"), "api-security")

        serialized = str(demo)
        self.assertNotIn(str(self.repo_root), serialized)
        self.assertNotIn("SECRET_KEY", serialized)
        self.assertNotIn("TOKEN", serialized.upper())
        self.assertNotIn("API_KEY", serialized.upper())

    def test_bootstrap_keeps_regular_database_out_of_demo_mode(self):
        bootstrap = self._bootstrap_payload(configured_database_path=self.repo_root / "data" / "outlook_accounts.db")
        demo = bootstrap.get("demo_workspace") or {}

        self.assertEqual(demo, {"enabled": False})


class DemoWorkspaceFrontendContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = import_web_app_module()
        cls.app = cls.module.app

    def _login(self, client, password: str = "testpass123") -> None:
        resp = client.post("/login", json={"password": password})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue((resp.get_json() or {}).get("success"))

    def _get_text(self, client, path: str) -> str:
        resp = client.get(path)
        try:
            return resp.data.decode("utf-8")
        finally:
            resp.close()

    def test_index_exposes_demo_workspace_mount(self):
        client = self.app.test_client()
        self._login(client)
        html = self._get_text(client, "/")

        self.assertIn('id="demoWorkspaceStrip"', html)
        self.assertIn('class="demo-workspace-strip"', html)
        self.assertIn('aria-live="polite"', html)
        self.assertLess(html.index('id="topbar"'), html.index('id="demoWorkspaceStrip"'))
        self.assertLess(html.index('id="demoWorkspaceStrip"'), html.index('id="refreshProgressBar"'))

    def test_main_js_consumes_bootstrap_and_wires_demo_actions(self):
        client = self.app.test_client()
        js = load_frontend_app_js()

        for expected in [
            "let appBootstrapState = null;",
            "window.__appBootstrap = data.bootstrap;",
            "const DEMO_WORKSPACE_ACTIONS",
            "function getDemoWorkspaceBootstrap()",
            "function renderDemoWorkspaceStrip()",
            "function handleDemoWorkspaceAction(actionKey)",
            "data-demo-workspace-action",
            "switchOverviewTab(action.tab)",
            "switchSettingsTab(action.tab)",
            "renderDemoWorkspaceStrip();",
        ]:
            self.assertIn(expected, js)

        init_slice = js[js.index("document.addEventListener('DOMContentLoaded'") : js.index("setTimeout(checkVersionUpdate")]
        self.assertLess(init_slice.index("await initLayoutState();"), init_slice.index("renderDemoWorkspaceStrip();"))

        helper_slice = js[
            js.index("function getDemoWorkspaceBootstrap()") : js.index("function applyAccountPanelDensityClasses")
        ]
        for forbidden in [
            "settingsExternalApiKey",
            "settingsExternalApiKeysJson",
            "settingsDuckmailBearerToken",
            "settingsEmailnatorApiKey",
            "settingsTempMailApiKey",
        ]:
            self.assertNotIn(forbidden, helper_slice)

    def test_css_defines_responsive_demo_workspace_strip(self):
        client = self.app.test_client()
        css = self._get_text(client, "/static/css/main.css")

        for expected in [
            ".demo-workspace-strip",
            ".demo-workspace-strip[hidden]",
            ".demo-workspace-actions",
            ".demo-workspace-action",
            "grid-template-columns: minmax(0, 1fr) auto;",
            "@media (max-width: 768px)",
            "grid-template-columns: repeat(2, minmax(0, 1fr));",
            "overflow-wrap: anywhere;",
            "white-space: normal;",
            ":focus-visible",
        ]:
            self.assertIn(expected, css)


if __name__ == "__main__":
    unittest.main()
