import json
import secrets
import unittest
from unittest.mock import patch

from tests._import_app import import_web_app_module


class TempMailboxPoolTests(unittest.TestCase):
    """临时邮箱（temp_emails 表）接入邮箱池的领取/释放/完成链路测试（Issue #85）。"""

    @classmethod
    def setUpClass(cls):
        cls.module = import_web_app_module()
        from outlook_web.db import create_sqlite_connection
        from outlook_web.repositories import pool as pool_repo
        from outlook_web.services import pool as pool_service

        cls.pool_repo = pool_repo
        cls.pool_service = pool_service
        cls.create_conn = staticmethod(lambda: create_sqlite_connection())

    def setUp(self):
        # 与共享临时 DB 的其它用例隔离：清理 accounts + temp_emails 池状态
        conn = self.create_conn()
        try:
            conn.execute("DELETE FROM account_project_usage")
            conn.execute("DELETE FROM account_claim_logs")
            conn.execute("DELETE FROM accounts")
            conn.execute("DELETE FROM temp_emails")
            conn.execute("DELETE FROM settings WHERE key = 'pool_default_provider'")
            conn.execute("DELETE FROM settings WHERE key = 'active_mailbox_providers'")
            conn.commit()
        finally:
            conn.close()

    def tearDown(self):
        conn = self.create_conn()
        try:
            conn.execute("DELETE FROM temp_emails")
            conn.commit()
        finally:
            conn.close()

    def _make_temp_email(self, source="custom_domain_temp_mail", domain=None, provider_name=None):
        # 每个邮箱使用唯一 domain，便于用 email_domain 过滤确定性领取
        if domain is None:
            domain = f"d{secrets.token_hex(4)}.test"
        conn = self.create_conn()
        try:
            local = f"u{secrets.token_hex(4)}"
            email = f"{local}@{domain}"
            meta_json = None
            if provider_name:
                meta_json = json.dumps({"provider_name": provider_name}, ensure_ascii=False)
            conn.execute(
                """
                INSERT INTO temp_emails (email, status, mailbox_type, source, prefix, domain, meta_json)
                VALUES (?, 'active', 'user', ?, ?, ?, ?)
                """,
                (email, source, local, domain, meta_json),
            )
            conn.commit()
            row = conn.execute("SELECT id FROM temp_emails WHERE email = ?", (email,)).fetchone()
            return row["id"], email, domain
        finally:
            conn.close()

    def _make_legacy_null_domain_email(self, domain):
        # 模拟老库：active 临时邮箱但 domain/prefix 为 NULL（v24 之前入库）
        conn = self.create_conn()
        try:
            local = f"legacy{secrets.token_hex(4)}"
            email = f"{local}@{domain}"
            conn.execute(
                """
                INSERT INTO temp_emails (email, status, mailbox_type, source, prefix, domain)
                VALUES (?, 'active', 'user', 'custom_domain_temp_mail', NULL, NULL)
                """,
                (email,),
            )
            conn.commit()
            row = conn.execute("SELECT id FROM temp_emails WHERE email = ?", (email,)).fetchone()
            return row["id"], email
        finally:
            conn.close()

    class _FakeDynamicTempProvider:
        def __init__(self, *, provider_name="duckmail", email="dyn@dynamic.test", success=True):
            self.provider_name = provider_name
            self.email = email
            self.success = success
            self.create_calls = []
            self.delete_calls = []

        def create_mailbox(self, *, prefix=None, domain=None):
            self.create_calls.append({"prefix": prefix, "domain": domain})
            if not self.success:
                return {
                    "success": False,
                    "error": "provider not configured",
                    "error_code": "TEMP_MAIL_PROVIDER_NOT_CONFIGURED",
                }
            return {
                "success": True,
                "email": self.email,
                "provider_name": self.provider_name,
                "meta": {
                    "provider_name": self.provider_name,
                    "provider_mailbox_id": "remote-1",
                    "provider_jwt": "jwt-1",
                    "provider_capabilities": {"delete_mailbox": True},
                },
            }

        def delete_mailbox(self, mailbox):
            self.delete_calls.append(mailbox)
            return True

    def test_claim_random_domain_filter_matches_null_domain_row(self):
        # 回归 (Issue #85 审查)：domain 为 NULL 的历史行按 email_domain 领取时不应漏掉
        domain = f"legacy{secrets.token_hex(4)}.test"
        temp_id, email = self._make_legacy_null_domain_email(domain)
        result = self.pool_service.claim_random(
            caller_id="reg_bot", task_id="t_null_dom", provider="custom", email_domain=domain
        )
        self.assertEqual(result["email"], email)
        self.assertEqual(result["id"], temp_id + self.pool_repo.TEMP_POOL_ID_OFFSET)

    def test_claim_random_custom_claims_temp_mailbox(self):
        temp_id, email, domain = self._make_temp_email()
        result = self.pool_service.claim_random(caller_id="reg_bot", task_id="t_claim", provider="custom", email_domain=domain)
        self.assertEqual(result["email"], email)
        self.assertEqual(result["id"], temp_id + self.pool_repo.TEMP_POOL_ID_OFFSET)
        self.assertTrue(result["claim_token"].startswith("clm_"))

        conn = self.create_conn()
        try:
            row = conn.execute("SELECT pool_status, claim_token FROM temp_emails WHERE id = ?", (temp_id,)).fetchone()
            self.assertEqual(row["pool_status"], "claimed")
            self.assertEqual(row["claim_token"], result["claim_token"])
        finally:
            conn.close()

    def test_claim_random_temp_provider_filters_by_provider_name(self):
        domain = f"provider{secrets.token_hex(4)}.test"
        self._make_temp_email(domain=domain, provider_name="mail_tm")
        duck_id, duck_email, _ = self._make_temp_email(domain=domain, provider_name="duckmail")

        result = self.pool_service.claim_random(
            caller_id="reg_bot",
            task_id="t_duck",
            provider="duckmail",
            email_domain=domain,
        )

        self.assertEqual(result["email"], duck_email)
        self.assertEqual(result["provider"], "duckmail")
        self.assertEqual(result["id"], duck_id + self.pool_repo.TEMP_POOL_ID_OFFSET)

    def test_claim_random_explicit_temp_provider_dynamically_creates_when_pool_empty(self):
        domain = f"dynamic{secrets.token_hex(4)}.test"
        email = f"created@{domain}"
        fake_provider = self._FakeDynamicTempProvider(provider_name="duckmail", email=email)

        with patch("outlook_web.services.pool.get_temp_mail_provider", return_value=fake_provider):
            result = self.pool_service.claim_random(
                caller_id="reg_bot",
                task_id="t_dynamic_duck",
                provider="duckmail",
                email_domain=domain,
            )

        self.assertEqual(result["email"], email)
        self.assertEqual(result["provider"], "duckmail")
        self.assertTrue(self.pool_repo.is_temp_pool_account_id(result["id"]))
        self.assertEqual(fake_provider.create_calls, [{"prefix": None, "domain": domain}])

        temp_id = self.pool_repo.temp_id_from_account_id(result["id"])
        conn = self.create_conn()
        try:
            row = conn.execute(
                """
                SELECT email, pool_status, claim_token, mailbox_type, visible_in_ui, meta_json
                FROM temp_emails
                WHERE id = ?
                """,
                (temp_id,),
            ).fetchone()
            self.assertEqual(row["email"], email)
            self.assertEqual(row["pool_status"], "claimed")
            self.assertEqual(row["claim_token"], result["claim_token"])
            self.assertEqual(row["mailbox_type"], "user")
            self.assertEqual(row["visible_in_ui"], 0)
            meta = json.loads(row["meta_json"])
            self.assertEqual(meta["provider_name"], "duckmail")
        finally:
            conn.close()

    def test_claim_random_auto_does_not_dynamically_create_temp_provider(self):
        with patch("outlook_web.services.pool.get_temp_mail_provider") as provider_factory:
            with self.assertRaises(self.pool_service.PoolServiceError) as ctx:
                self.pool_service.claim_random(caller_id="reg_bot", task_id="t_auto_empty", provider="auto")

        self.assertEqual(ctx.exception.error_code, "no_available_account")
        provider_factory.assert_not_called()

    def test_claim_random_temp_provider_create_failure_uses_stable_pool_error(self):
        fake_provider = self._FakeDynamicTempProvider(provider_name="duckmail", success=False)

        with patch("outlook_web.services.pool.get_temp_mail_provider", return_value=fake_provider):
            with self.assertRaises(self.pool_service.PoolServiceError) as ctx:
                self.pool_service.claim_random(
                    caller_id="reg_bot",
                    task_id="t_dynamic_fail",
                    provider="duckmail",
                )

        self.assertEqual(ctx.exception.error_code, "TEMP_MAIL_PROVIDER_NOT_CONFIGURED")
        self.assertEqual(ctx.exception.http_status, 502)

    def test_claim_random_temp_provider_dynamic_create_rejects_domain_mismatch(self):
        fake_provider = self._FakeDynamicTempProvider(provider_name="duckmail", email="created@wrong.test")

        with patch("outlook_web.services.pool.get_temp_mail_provider", return_value=fake_provider):
            with self.assertRaises(self.pool_service.PoolServiceError) as ctx:
                self.pool_service.claim_random(
                    caller_id="reg_bot",
                    task_id="t_dynamic_domain_mismatch",
                    provider="duckmail",
                    email_domain="wanted.test",
                )

        self.assertEqual(ctx.exception.error_code, "UPSTREAM_BAD_PAYLOAD")
        self.assertEqual(len(fake_provider.delete_calls), 1)

    def test_claim_random_custom_does_not_claim_other_temp_provider(self):
        _, _, domain = self._make_temp_email(provider_name="duckmail")

        with self.assertRaises(self.pool_service.PoolServiceError) as ctx:
            self.pool_service.claim_random(caller_id="reg_bot", task_id="t_custom_strict", provider="custom", email_domain=domain)

        self.assertEqual(ctx.exception.error_code, "no_available_account")

    def test_claim_random_provider_none_claims_temp_mailbox(self):
        temp_id, email, domain = self._make_temp_email()
        result = self.pool_service.claim_random(caller_id="reg_bot", task_id="t_none", email_domain=domain)
        self.assertTrue(self.pool_repo.is_temp_pool_account_id(result["id"]))

    def test_claim_random_uses_pool_default_provider_when_request_omits_provider(self):
        domain = f"default{secrets.token_hex(4)}.test"
        self._make_temp_email(domain=domain, provider_name="mail_tm")
        duck_id, duck_email, _ = self._make_temp_email(domain=domain, provider_name="duckmail")
        conn = self.create_conn()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES ('pool_default_provider', 'duckmail', CURRENT_TIMESTAMP)"
            )
            conn.commit()
        finally:
            conn.close()

        result = self.pool_service.claim_random(caller_id="reg_bot", task_id="t_default_provider", email_domain=domain)

        self.assertEqual(result["email"], duck_email)
        self.assertEqual(result["provider"], "duckmail")
        self.assertEqual(result["id"], duck_id + self.pool_repo.TEMP_POOL_ID_OFFSET)

    def test_claim_random_explicit_provider_overrides_pool_default_provider(self):
        domain = f"override{secrets.token_hex(4)}.test"
        mail_id, mail_email, _ = self._make_temp_email(domain=domain, provider_name="mail_tm")
        self._make_temp_email(domain=domain, provider_name="duckmail")
        conn = self.create_conn()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES ('pool_default_provider', 'duckmail', CURRENT_TIMESTAMP)"
            )
            conn.commit()
        finally:
            conn.close()

        result = self.pool_service.claim_random(
            caller_id="reg_bot",
            task_id="t_explicit_provider",
            provider="mail_tm",
            email_domain=domain,
        )

        self.assertEqual(result["email"], mail_email)
        self.assertEqual(result["provider"], "mail_tm")
        self.assertEqual(result["id"], mail_id + self.pool_repo.TEMP_POOL_ID_OFFSET)

    def test_claim_random_pool_default_gptmail_keeps_temp_family_alias_semantics(self):
        domain = f"legacy{secrets.token_hex(4)}.test"
        temp_id, email, _ = self._make_temp_email(domain=domain, provider_name="custom_domain_temp_mail")
        self._make_temp_email(domain=domain, provider_name="duckmail")
        conn = self.create_conn()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES ('pool_default_provider', 'gptmail', CURRENT_TIMESTAMP)"
            )
            conn.commit()
        finally:
            conn.close()

        result = self.pool_service.claim_random(caller_id="reg_bot", task_id="t_default_gptmail", email_domain=domain)

        self.assertEqual(result["email"], email)
        self.assertEqual(result["provider"], "custom_domain_temp_mail")
        self.assertEqual(result["id"], temp_id + self.pool_repo.TEMP_POOL_ID_OFFSET)

    def test_claim_random_outlook_does_not_touch_temp(self):
        # 制造一个可用临时邮箱（唯一 domain），provider=outlook 不应回退到临时邮箱池
        _, _, domain = self._make_temp_email()
        with self.assertRaises(self.pool_service.PoolServiceError) as ctx:
            self.pool_service.claim_random(caller_id="reg_bot", task_id="t_outlook", provider="outlook", email_domain=domain)
        self.assertEqual(ctx.exception.error_code, "no_available_account")

    def test_claim_random_imap_does_not_touch_temp(self):
        # provider=imap 是账号池兼容别名，不应被当作临时邮箱 provider 回退领取。
        _, _, domain = self._make_temp_email()
        with self.assertRaises(self.pool_service.PoolServiceError) as ctx:
            self.pool_service.claim_random(caller_id="reg_bot", task_id="t_imap", provider="imap", email_domain=domain)
        self.assertEqual(ctx.exception.error_code, "no_available_account")

    def test_claim_random_active_provider_filter_limits_auto_temp_claim(self):
        domain = f"active{secrets.token_hex(4)}.test"
        self._make_temp_email(domain=domain, provider_name="mail_tm")
        duck_id, duck_email, _ = self._make_temp_email(domain=domain, provider_name="duckmail")
        conn = self.create_conn()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES ('active_mailbox_providers', 'duckmail', CURRENT_TIMESTAMP)"
            )
            conn.commit()
        finally:
            conn.close()

        result = self.pool_service.claim_random(caller_id="reg_bot", task_id="t_active_auto", provider="auto", email_domain=domain)

        self.assertEqual(result["email"], duck_email)
        self.assertEqual(result["provider"], "duckmail")
        self.assertEqual(result["id"], duck_id + self.pool_repo.TEMP_POOL_ID_OFFSET)

    def test_claim_random_rejects_inactive_explicit_temp_provider(self):
        conn = self.create_conn()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES ('active_mailbox_providers', 'duckmail', CURRENT_TIMESTAMP)"
            )
            conn.commit()
        finally:
            conn.close()

        with self.assertRaises(self.pool_service.PoolServiceError) as ctx:
            self.pool_service.claim_random(caller_id="reg_bot", task_id="t_inactive", provider="mail_tm")

        self.assertEqual(ctx.exception.error_code, "provider_not_active")

    def test_claim_random_imap_alias_claims_imap_account_family(self):
        conn = self.create_conn()
        try:
            conn.execute(
                """
                INSERT INTO accounts (email, password, client_id, refresh_token, account_type, provider, status, pool_status)
                VALUES ('gmail-imap@test.local', 'pw', '', '', 'imap', 'gmail', 'active', 'available')
                """
            )
            conn.commit()
        finally:
            conn.close()

        result = self.pool_service.claim_random(caller_id="reg_bot", task_id="t_imap_alias", provider="imap")

        self.assertEqual(result["email"], "gmail-imap@test.local")
        self.assertEqual(result["provider"], "gmail")

    def test_release_temp_mailbox(self):
        _, _, domain = self._make_temp_email()
        claimed = self.pool_service.claim_random(caller_id="reg_bot", task_id="t_rel", provider="custom", email_domain=domain)
        self.pool_service.release_claim(
            account_id=claimed["id"],
            claim_token=claimed["claim_token"],
            caller_id="reg_bot",
            task_id="t_rel",
        )
        temp_id = self.pool_repo.temp_id_from_account_id(claimed["id"])
        conn = self.create_conn()
        try:
            row = conn.execute("SELECT pool_status, claim_token FROM temp_emails WHERE id = ?", (temp_id,)).fetchone()
            self.assertEqual(row["pool_status"], "available")
            self.assertIsNone(row["claim_token"])
        finally:
            conn.close()

    def test_complete_temp_mailbox_success(self):
        _, _, domain = self._make_temp_email()
        claimed = self.pool_service.claim_random(caller_id="reg_bot", task_id="t_done", provider="custom", email_domain=domain)
        new_status = self.pool_service.complete_claim(
            account_id=claimed["id"],
            claim_token=claimed["claim_token"],
            caller_id="reg_bot",
            task_id="t_done",
            result="success",
        )
        self.assertEqual(new_status, "used")
        temp_id = self.pool_repo.temp_id_from_account_id(claimed["id"])
        conn = self.create_conn()
        try:
            row = conn.execute("SELECT pool_status, last_result FROM temp_emails WHERE id = ?", (temp_id,)).fetchone()
            self.assertEqual(row["pool_status"], "used")
            self.assertEqual(row["last_result"], "success")
        finally:
            conn.close()

    def test_complete_temp_mailbox_token_mismatch(self):
        _, _, domain = self._make_temp_email()
        claimed = self.pool_service.claim_random(caller_id="reg_bot", task_id="t_mm", provider="custom", email_domain=domain)
        with self.assertRaises(self.pool_service.PoolServiceError) as ctx:
            self.pool_service.complete_claim(
                account_id=claimed["id"],
                claim_token="clm_wrong",
                caller_id="reg_bot",
                task_id="t_mm",
                result="success",
            )
        self.assertEqual(ctx.exception.error_code, "token_mismatch")

    def test_get_claim_context_resolves_temp(self):
        _, _, domain = self._make_temp_email()
        claimed = self.pool_service.claim_random(caller_id="reg_bot", task_id="t_ctx", provider="custom", email_domain=domain)
        conn = self.create_conn()
        try:
            ctx = self.pool_repo.get_claim_context(conn, claimed["claim_token"])
        finally:
            conn.close()
        self.assertIsNotNone(ctx)
        self.assertEqual(ctx["account_id"], claimed["id"])
        self.assertEqual(ctx["email"], claimed["email"])

    def test_expire_and_recover_temp(self):
        _, _, domain = self._make_temp_email()
        # 领取并将租约设为已过期
        claimed = self.pool_service.claim_random(caller_id="reg_bot", task_id="t_exp", provider="custom", email_domain=domain)
        temp_id = self.pool_repo.temp_id_from_account_id(claimed["id"])
        conn = self.create_conn()
        try:
            conn.execute(
                "UPDATE temp_emails SET lease_expires_at = '2000-01-01T00:00:00Z' WHERE id = ?",
                (temp_id,),
            )
            conn.commit()
            expired = self.pool_repo.expire_stale_temp_claims(conn)
            self.assertGreaterEqual(expired, 1)
            row = conn.execute("SELECT pool_status, updated_at FROM temp_emails WHERE id = ?", (temp_id,)).fetchone()
            self.assertEqual(row["pool_status"], "cooldown")
            # 冷却结束后恢复
            conn.execute(
                "UPDATE temp_emails SET updated_at = '2000-01-01T00:00:00Z' WHERE id = ?",
                (temp_id,),
            )
            conn.commit()
            recovered = self.pool_repo.recover_cooldown_temp(conn, cooldown_seconds=60)
            self.assertGreaterEqual(recovered, 1)
            row2 = conn.execute("SELECT pool_status FROM temp_emails WHERE id = ?", (temp_id,)).fetchone()
            self.assertEqual(row2["pool_status"], "available")
        finally:
            conn.close()

    def test_stats_includes_temp(self):
        self._make_temp_email()
        stats = self.pool_service.get_pool_stats()
        self.assertGreaterEqual(stats["pool_counts"]["available"], 1)


if __name__ == "__main__":
    unittest.main()
