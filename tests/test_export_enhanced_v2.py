"""tests/test_export_enhanced_v2.py — FD-00006 导出 v2 增强测试"""

import unittest

from tests._import_app import clear_login_attempts, import_web_app_module


class TestExportEnhancedV2(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = import_web_app_module()
        cls.app = cls.module.app

    def setUp(self):
        with self.app.app_context():
            clear_login_attempts()

    def test_build_export_text_v2_header(self):
        """导出文本包含 v2 头部元信息"""
        with self.app.app_context():
            from mailops.controllers.accounts import _build_export_text

            accounts = [
                {
                    "email": "test@outlook.com",
                    "password": "pwd",
                    "client_id": "cid",
                    "refresh_token": "rt",
                    "account_type": "outlook",
                    "provider": "outlook",
                },
            ]
            content = _build_export_text(accounts)
            self.assertIn("# Outlook Email Plus — 账号导出", content)
            self.assertIn("# 格式版本：v2", content)
            self.assertIn("# 账号总数：1", content)
            self.assertIn("Outlook：1", content)

    def test_build_export_text_v2_outlook_section(self):
        """Outlook 分段格式不变"""
        with self.app.app_context():
            from mailops.controllers.accounts import _build_export_text

            accounts = [
                {
                    "email": "a@outlook.com",
                    "password": "p",
                    "client_id": "c",
                    "refresh_token": "r",
                    "account_type": "outlook",
                    "provider": "outlook",
                },
            ]
            content = _build_export_text(accounts)
            self.assertIn("# === Outlook 账号 ===", content)
            self.assertIn("a@outlook.com----p----c----r", content)

    def test_build_export_text_v2_imap_section(self):
        """IMAP 分段格式正确"""
        with self.app.app_context():
            from mailops.controllers.accounts import _build_export_text

            accounts = [
                {
                    "email": "a@gmail.com",
                    "imap_password": "imap_pwd",
                    "account_type": "imap",
                    "provider": "gmail",
                },
            ]
            content = _build_export_text(accounts)
            self.assertIn("# === IMAP 账号（Gmail）===", content)
            self.assertIn("a@gmail.com----imap_pwd----gmail", content)

    def test_build_export_text_v2_custom_5_segment(self):
        """Custom IMAP 输出 5 段"""
        with self.app.app_context():
            from mailops.controllers.accounts import _build_export_text

            accounts = [
                {
                    "email": "a@corp.com",
                    "imap_password": "pwd",
                    "account_type": "imap",
                    "provider": "custom",
                    "imap_host": "mail.corp.com",
                    "imap_port": 995,
                },
            ]
            content = _build_export_text(accounts)
            self.assertIn("a@corp.com----pwd----custom----mail.corp.com----995", content)

    def test_build_export_text_v2_temp_mail_section(self):
        """临时邮箱分段仅邮箱地址"""
        with self.app.app_context():
            from mailops.controllers.accounts import _build_export_text

            temp_emails = [{"email": "t1@temp.example"}, {"email": "t2@temp.example"}]
            content = _build_export_text([], temp_emails)
            self.assertIn("# === 临时邮箱（兼容临时邮箱桥接）===", content)
            self.assertIn("t1@temp.example", content)
            self.assertIn("t2@temp.example", content)
            # 临时邮箱行不应包含 ----
            for line in content.split("\n"):
                if "@temp.example" in line and not line.startswith("#"):
                    self.assertNotIn("----", line)

    def test_build_export_text_v2_temp_mail_sections_are_provider_aware(self):
        """临时邮箱导出标题应反映真实 Provider，避免把公共服务误标为自建。"""
        with self.app.app_context():
            from mailops.controllers.accounts import _build_export_text

            temp_emails = [
                {"email": "duck@temp.example", "provider_name": "duckmail"},
                {"email": "nator@temp.example", "meta": {"provider_name": "emailnator"}},
            ]
            content = _build_export_text([], temp_emails)

            self.assertIn("# === 临时邮箱（DuckMail）===", content)
            self.assertIn("# === 临时邮箱（Emailnator）===", content)
            self.assertNotIn("# === 临时邮箱（自建）===", content)
            self.assertIn("duck@temp.example", content)
            self.assertIn("nator@temp.example", content)

    def test_build_export_text_v2_cloudflare_pool_account_exports_as_temp_mail(self):
        """accounts 表中的 CF 临时邮箱不应被误导出为普通 IMAP。"""
        with self.app.app_context():
            from mailops.controllers.accounts import _build_export_text

            accounts = [
                {
                    "email": "cf@temp.example",
                    "account_type": "temp_mail",
                    "provider": "cloudflare_temp_mail",
                }
            ]
            content = _build_export_text(accounts)

            self.assertIn("# === 临时邮箱（Cloudflare Temp Mail）===", content)
            self.assertIn("cf@temp.example", content)
            self.assertNotIn("# === IMAP 账号", content)

    def test_build_export_text_v2_regular_imap_wins_provider_name_collision(self):
        """普通邮箱 provider 与临时邮箱插件撞名时，account_type=imap 仍按普通邮箱导出。"""
        with self.app.app_context():
            from mailops.controllers.accounts import _build_export_text
            from mailops.services.temp_mail_provider_base import _REGISTRY, register_provider

            original_gmail_provider = _REGISTRY.get("gmail")

            @register_provider
            class Gmail:
                provider_name = "gmail"
                provider_label = "Fake Gmail Temp"

            try:
                content = _build_export_text(
                    [
                        {
                            "email": "imap@gmail.com",
                            "imap_password": "pw",
                            "account_type": "imap",
                            "provider": "gmail",
                        }
                    ]
                )
            finally:
                if original_gmail_provider is not None:
                    _REGISTRY["gmail"] = original_gmail_provider
                else:
                    _REGISTRY.pop("gmail", None)

            self.assertIn("# === IMAP 账号（Gmail）===", content)
            self.assertIn("imap@gmail.com----pw----gmail", content)
            self.assertNotIn("Fake Gmail Temp", content)

    def test_build_export_text_v2_mixed_counts(self):
        """混合账号统计正确"""
        with self.app.app_context():
            from mailops.controllers.accounts import _build_export_text

            accounts = [
                {
                    "email": "a@o.com",
                    "password": "p",
                    "client_id": "c",
                    "refresh_token": "r",
                    "account_type": "outlook",
                    "provider": "outlook",
                },
                {
                    "email": "b@o.com",
                    "password": "p",
                    "client_id": "c",
                    "refresh_token": "r",
                    "account_type": "outlook",
                    "provider": "outlook",
                },
                {"email": "c@gmail.com", "imap_password": "ip", "account_type": "imap", "provider": "gmail"},
            ]
            temp_emails = [{"email": "t@temp.example"}]
            content = _build_export_text(accounts, temp_emails)
            self.assertIn("# 账号总数：4", content)
            self.assertIn("Outlook：2", content)
            self.assertIn("Gmail：1", content)
            self.assertIn("临时邮箱：1", content)

    def test_export_ends_with_newline(self):
        """导出文件末尾有换行"""
        with self.app.app_context():
            from mailops.controllers.accounts import _build_export_text

            accounts = [
                {
                    "email": "a@o.com",
                    "password": "p",
                    "client_id": "c",
                    "refresh_token": "r",
                    "account_type": "outlook",
                    "provider": "outlook",
                },
            ]
            content = _build_export_text(accounts)
            self.assertTrue(content.endswith("\n"))


if __name__ == "__main__":
    unittest.main()
