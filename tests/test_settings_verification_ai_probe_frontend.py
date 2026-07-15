from __future__ import annotations

from tests.frontend_js_bundle import load_frontend_app_js
import unittest

from tests._import_app import import_web_app_module


class SettingsVerificationAiProbeFrontendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = import_web_app_module()
        cls.app = cls.module.app

    def _login(self, client, password: str = "testpass123"):
        resp = client.post("/login", json={"password": password})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json().get("success"))

    def test_settings_page_contains_verification_ai_test_button(self):
        client = self.app.test_client()
        self._login(client)

        resp = client.get("/")
        html = resp.data.decode("utf-8")

        self.assertIn('id="btnTestVerificationAi"', html)
        self.assertIn('id="verificationAiTestResult"', html)
        self.assertIn("测试 AI 配置", html)

    def test_main_js_contains_verification_ai_test_function_and_endpoint(self):
        client = self.app.test_client()
        js = load_frontend_app_js()

        self.assertIn("function testVerificationAiConfig", js)
        self.assertIn("/api/settings/verification-ai-test", js)
        # Result chrome translates at paint time for English UI.
        fn_start = js.index("async function testVerificationAiConfig()")
        fn_end = js.index("async function syncCfWorkerDomains()", fn_start)
        fn_slice = js[fn_start:fn_end]
        self.assertIn("translateAppTextLocal('正在验证已保存的 AI 配置连通性...')", fn_slice)
        self.assertIn("translateAppTextLocal('AI 配置测试失败')", fn_slice)
        self.assertIn("translateAppTextLocal(connectivityOnly ? 'AI 连通性测试成功' : 'AI 配置测试成功')", fn_slice)
        self.assertIn("translateAppTextLocal('请填写 AI Base URL')", js)
        self.assertIn("translateAppTextLocal('请填写 AI 模型 ID')", js)
        self.assertIn("translateAppTextLocal('请填写 AI API Key')", js)


if __name__ == "__main__":
    unittest.main()
