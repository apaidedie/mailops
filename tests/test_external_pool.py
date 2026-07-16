import json
import unittest
import uuid
from unittest.mock import patch

from tests._import_app import clear_login_attempts, import_web_app_module

CANONICAL_EXTERNAL_PREFIX = "/api/v1/external"


class ExternalPoolApiTests(unittest.TestCase):
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
            db.execute("DELETE FROM audit_logs WHERE resource_type = 'external_api'")
            db.execute("DELETE FROM external_api_keys")
            db.execute("DELETE FROM external_api_consumer_usage_daily")
            db.execute(
                "DELETE FROM account_claim_logs WHERE account_id IN (SELECT id FROM accounts WHERE email LIKE '%@extpool.test')"
            )
            db.execute("DELETE FROM accounts WHERE email LIKE '%@extpool.test'")
            db.execute("DELETE FROM temp_email_messages WHERE email_address LIKE '%@extpool.test'")
            db.execute("DELETE FROM temp_emails WHERE email LIKE '%@extpool.test'")
            db.commit()
            settings_repo.set_setting("external_api_key", "")
            settings_repo.set_setting("external_api_public_mode", "false")
            settings_repo.set_setting("pool_external_enabled", "false")
            settings_repo.set_setting("external_api_ip_whitelist", "[]")
            settings_repo.set_setting("external_api_disable_pool_claim_random", "false")
            settings_repo.set_setting("external_api_disable_pool_claim_release", "false")
            settings_repo.set_setting("external_api_disable_pool_claim_complete", "false")
            settings_repo.set_setting("external_api_disable_pool_stats", "false")
            settings_repo.set_setting("pool_default_provider", "")

    @staticmethod
    def _auth_headers(value: str = "abc123"):
        return {"X-API-Key": value}

    def _set_external_api_key(self, value: str):
        with self.app.app_context():
            from outlook_web.repositories import settings as settings_repo

            settings_repo.set_setting("external_api_key", value)

    def _create_external_api_key(
        self,
        name: str,
        api_key: str,
        *,
        pool_access: bool = False,
        enabled: bool = True,
    ):
        with self.app.app_context():
            from outlook_web.repositories import external_api_keys as external_api_keys_repo

            return external_api_keys_repo.create_external_api_key(
                name=name,
                api_key=api_key,
                allowed_emails=[],
                pool_access=pool_access,
                enabled=enabled,
            )

    def _set_public_mode(self, enabled: bool):
        with self.app.app_context():
            from outlook_web.repositories import settings as settings_repo

            settings_repo.set_setting("external_api_public_mode", "true" if enabled else "false")

    def _set_ip_whitelist(self, ips: list[str]):
        import json

        with self.app.app_context():
            from outlook_web.repositories import settings as settings_repo

            settings_repo.set_setting("external_api_ip_whitelist", json.dumps(ips))

    def _set_disable_feature(self, setting_key: str, enabled: bool):
        with self.app.app_context():
            from outlook_web.repositories import settings as settings_repo

            settings_repo.set_setting(setting_key, "true" if enabled else "false")

    def _insert_pool_account(
        self,
        *,
        provider: str = "outlook",
        pool_status: str = "available",
        account_type: str = "outlook",
    ) -> int:
        email_addr = f"{uuid.uuid4().hex}@extpool.test"
        with self.app.app_context():
            from outlook_web.db import get_db

            db = get_db()
            db.execute(
                """
                INSERT INTO accounts (
                    email, password, client_id, refresh_token,
                    group_id, status, account_type, provider, pool_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    email_addr,
                    "pw",
                    "cid-test",
                    "rt-test",
                    1,
                    "active",
                    account_type,
                    provider,
                    pool_status,
                ),
            )
            db.commit()
            row = db.execute("SELECT id FROM accounts WHERE email = ?", (email_addr,)).fetchone()
            return int(row["id"])

    def _insert_temp_mailbox(self, *, provider_name: str = "duckmail", domain: str = "extpool.test") -> str:
        email_addr = f"{uuid.uuid4().hex}@{domain}"
        prefix = email_addr.split("@", 1)[0]
        with self.app.app_context():
            from outlook_web.db import get_db

            db = get_db()
            db.execute(
                """
                INSERT INTO temp_emails (email, status, mailbox_type, source, prefix, domain, meta_json)
                VALUES (?, 'active', 'user', 'custom_domain_temp_mail', ?, ?, ?)
                """,
                (email_addr, prefix, domain, json.dumps({"provider_name": provider_name}, ensure_ascii=False)),
            )
            db.commit()
        return email_addr

    class _FakePoolTempProvider:
        provider_name = "duckmail"

        def __init__(self, email: str):
            self.email = email

        def create_mailbox(self, *, prefix=None, domain=None):
            return {
                "success": True,
                "email": self.email,
                "provider_name": self.provider_name,
                "meta": {"provider_name": self.provider_name, "provider_mailbox_id": "duck-remote-1"},
            }

        def delete_mailbox(self, mailbox):
            return True

    def test_old_anonymous_pool_endpoints_are_removed(self):
        client = self.app.test_client()

        endpoints = [
            ("get", "/api/pool/stats", None),
            ("post", "/api/pool/claim-random", {"caller_id": "legacy", "task_id": "removed-random"}),
            (
                "post",
                "/api/pool/claim-release",
                {"account_id": 1, "claim_token": "clm_old", "caller_id": "legacy", "task_id": "removed-release"},
            ),
            (
                "post",
                "/api/pool/claim-complete",
                {
                    "account_id": 1,
                    "claim_token": "clm_old",
                    "caller_id": "legacy",
                    "task_id": "removed-complete",
                    "result": "success",
                },
            ),
        ]

        for method, path, payload in endpoints:
            if method == "get":
                resp = client.get(path)
            else:
                resp = client.post(path, json=payload)
            self.assertEqual(resp.status_code, 404, msg=f"{path} should return 404 after removal")

    def test_external_pool_stats_requires_api_key(self):
        client = self.app.test_client()
        self._set_external_api_key("abc123")

        resp = client.get("/api/v1/external/pool/stats")

        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.get_json().get("code"), "UNAUTHORIZED")

    def test_external_pool_claim_release_requires_api_key(self):
        client = self.app.test_client()
        self._set_external_api_key("abc123")
        with self.app.app_context():
            from outlook_web.repositories import settings as settings_repo

            settings_repo.set_setting("pool_external_enabled", "true")
        self._insert_pool_account(provider="outlook")

        claim_resp = client.post(
            "/api/v1/external/pool/claim-random",
            headers=self._auth_headers(),
            json={"caller_id": "ext-worker-01", "task_id": "release-no-key", "provider": "outlook"},
        )
        self.assertEqual(claim_resp.status_code, 200)
        claim_data = claim_resp.get_json()["data"]

        resp = client.post(
            "/api/v1/external/pool/claim-release",
            json={
                "account_id": claim_data["account_id"],
                "claim_token": claim_data["claim_token"],
                "caller_id": "ext-worker-01",
                "task_id": "release-no-key",
            },
        )

        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.get_json().get("code"), "UNAUTHORIZED")

    def test_external_pool_claim_complete_requires_api_key(self):
        client = self.app.test_client()
        self._set_external_api_key("abc123")
        with self.app.app_context():
            from outlook_web.repositories import settings as settings_repo

            settings_repo.set_setting("pool_external_enabled", "true")
        self._insert_pool_account(provider="outlook")

        claim_resp = client.post(
            "/api/v1/external/pool/claim-random",
            headers=self._auth_headers(),
            json={"caller_id": "ext-worker-01", "task_id": "complete-no-key", "provider": "outlook"},
        )
        self.assertEqual(claim_resp.status_code, 200)
        claim_data = claim_resp.get_json()["data"]

        resp = client.post(
            "/api/v1/external/pool/claim-complete",
            json={
                "account_id": claim_data["account_id"],
                "claim_token": claim_data["claim_token"],
                "caller_id": "ext-worker-01",
                "task_id": "complete-no-key",
                "result": "success",
            },
        )

        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.get_json().get("code"), "UNAUTHORIZED")

    def test_external_pool_claim_random_success(self):
        client = self.app.test_client()
        self._set_external_api_key("abc123")
        with self.app.app_context():
            from outlook_web.repositories import settings as settings_repo

            settings_repo.set_setting("pool_external_enabled", "true")
        self._insert_pool_account(provider="outlook")

        resp = client.post(
            "/api/v1/external/pool/claim-random",
            headers=self._auth_headers(),
            json={
                "caller_id": "ext-worker-01",
                "task_id": "task-ext-001",
                "provider": "outlook",
            },
        )

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("code"), "OK")
        payload = data.get("data", {})
        self.assertIn("account_id", payload)
        self.assertIn("claim_token", payload)
        self.assertIn("lease_expires_at", payload)
        contract = payload.get("external_mailbox_read_contract") or {}
        self.assertEqual(contract.get("read_by"), ["email", "claim_token"])
        self.assertEqual(
            contract.get("next_actions", {}).get("read_messages", {}).get("endpoint"), f"{CANONICAL_EXTERNAL_PREFIX}/messages"
        )
        self.assertEqual(
            contract.get("next_actions", {}).get("release_claim", {}).get("endpoint"),
            f"{CANONICAL_EXTERNAL_PREFIX}/pool/claim-release",
        )
        self.assertEqual(
            contract.get("next_actions", {}).get("complete_claim", {}).get("endpoint"),
            f"{CANONICAL_EXTERNAL_PREFIX}/pool/claim-complete",
        )

    def test_external_pool_claim_random_rejects_non_object_json_body(self):
        client = self.app.test_client()
        self._set_external_api_key("abc123")
        with self.app.app_context():
            from outlook_web.repositories import settings as settings_repo

            settings_repo.set_setting("pool_external_enabled", "true")

        resp = client.post(
            "/api/v1/external/pool/claim-random",
            headers={**self._auth_headers(), "Content-Type": "application/json"},
            data="[]",
        )

        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.get_json()["code"], "INVALID_PARAM")

    def test_external_pool_claim_random_accepts_catalog_account_provider(self):
        client = self.app.test_client()
        self._set_external_api_key("abc123")
        with self.app.app_context():
            from outlook_web.repositories import settings as settings_repo

            settings_repo.set_setting("pool_external_enabled", "true")
        self._insert_pool_account(provider="gmail", account_type="imap")

        resp = client.post(
            "/api/v1/external/pool/claim-random",
            headers=self._auth_headers(),
            json={
                "caller_id": "ext-worker-01",
                "task_id": "task-gmail-provider",
                "provider": "gmail",
            },
        )

        self.assertEqual(resp.status_code, 200)
        payload = resp.get_json().get("data", {})
        self.assertEqual(payload.get("provider"), "gmail")
        self.assertEqual(payload.get("provider_label"), "Gmail")
        self.assertEqual(payload.get("read_capability"), "imap")

    def test_external_pool_claim_random_accepts_auto_provider_from_catalog(self):
        client = self.app.test_client()
        self._set_external_api_key("abc123")
        with self.app.app_context():
            from outlook_web.repositories import settings as settings_repo

            settings_repo.set_setting("pool_external_enabled", "true")
        self._insert_pool_account(provider="gmail", account_type="imap")

        resp = client.post(
            "/api/v1/external/pool/claim-random",
            headers=self._auth_headers(),
            json={
                "caller_id": "ext-worker-01",
                "task_id": "task-auto-provider",
                "provider": "auto",
            },
        )

        self.assertEqual(resp.status_code, 200)
        payload = resp.get_json().get("data", {})
        self.assertEqual(payload.get("provider"), "gmail")
        self.assertEqual(payload.get("read_capability"), "imap")

    def test_external_pool_claim_random_omitted_provider_uses_pool_default_provider(self):
        client = self.app.test_client()
        self._set_external_api_key("abc123")
        with self.app.app_context():
            from outlook_web.repositories import settings as settings_repo

            settings_repo.set_setting("pool_external_enabled", "true")
            settings_repo.set_setting("pool_default_provider", "duckmail")
        email_addr = self._insert_temp_mailbox(provider_name="duckmail")

        resp = client.post(
            "/api/v1/external/pool/claim-random",
            headers=self._auth_headers(),
            json={
                "caller_id": "ext-worker-01",
                "task_id": "task-default-provider",
            },
        )

        self.assertEqual(resp.status_code, 200)
        payload = resp.get_json().get("data", {})
        self.assertEqual(payload.get("email"), email_addr)
        self.assertEqual(payload.get("provider"), "duckmail")

    def test_external_pool_claim_random_null_provider_bypasses_pool_default_provider(self):
        client = self.app.test_client()
        self._set_external_api_key("abc123")
        with self.app.app_context():
            from outlook_web.repositories import settings as settings_repo

            settings_repo.set_setting("pool_external_enabled", "true")
            settings_repo.set_setting("pool_default_provider", "duckmail")
        self._insert_pool_account(provider="outlook")
        self._insert_temp_mailbox(provider_name="duckmail")

        resp = client.post(
            "/api/v1/external/pool/claim-random",
            headers=self._auth_headers(),
            json={
                "caller_id": "ext-worker-01",
                "task_id": "task-null-provider",
                "provider": None,
            },
        )

        self.assertEqual(resp.status_code, 200)
        payload = resp.get_json().get("data", {})
        self.assertEqual(payload.get("provider"), "outlook")
        self.assertEqual(payload.get("read_capability"), "graph")

    def test_external_pool_claim_random_accepts_temp_provider(self):
        client = self.app.test_client()
        self._set_external_api_key("abc123")
        with self.app.app_context():
            from outlook_web.repositories import settings as settings_repo

            settings_repo.set_setting("pool_external_enabled", "true")
        email_addr = self._insert_temp_mailbox(provider_name="duckmail")

        resp = client.post(
            "/api/v1/external/pool/claim-random",
            headers=self._auth_headers(),
            json={
                "caller_id": "ext-worker-01",
                "task_id": "task-duck-provider",
                "provider": "duckmail",
            },
        )

        self.assertEqual(resp.status_code, 200)
        payload = resp.get_json().get("data", {})
        self.assertEqual(payload.get("email"), email_addr)
        self.assertEqual(payload.get("provider"), "duckmail")
        self.assertEqual(payload.get("provider_label"), "DuckMail")
        self.assertEqual(payload.get("read_capability"), "temp_provider")

    def test_external_pool_claim_random_dynamic_creates_explicit_temp_provider(self):
        client = self.app.test_client()
        self._set_external_api_key("abc123")
        with self.app.app_context():
            from outlook_web.repositories import settings as settings_repo

            settings_repo.set_setting("pool_external_enabled", "true")
        email_addr = f"created-{uuid.uuid4().hex}@extpool.test"

        with patch(
            "outlook_web.services.pool.get_temp_mail_provider",
            return_value=self._FakePoolTempProvider(email_addr),
        ):
            resp = client.post(
                "/api/v1/external/pool/claim-random",
                headers=self._auth_headers(),
                json={
                    "caller_id": "ext-worker-01",
                    "task_id": "task-duck-dynamic",
                    "provider": "duckmail",
                    "email_domain": "extpool.test",
                },
            )

        self.assertEqual(resp.status_code, 200)
        payload = resp.get_json().get("data", {})
        self.assertEqual(payload.get("email"), email_addr)
        self.assertEqual(payload.get("provider"), "duckmail")
        self.assertEqual(payload.get("provider_label"), "DuckMail")
        self.assertEqual(payload.get("read_capability"), "temp_provider")
        self.assertGreaterEqual(int(payload.get("account_id") or 0), 1_000_000_000)

    def test_external_pool_post_does_not_require_csrf(self):
        client = self.app.test_client()
        self._set_external_api_key("abc123")
        with self.app.app_context():
            from outlook_web.repositories import settings as settings_repo

            settings_repo.set_setting("pool_external_enabled", "true")
        self._insert_pool_account(provider="outlook")

        resp = client.post(
            "/api/v1/external/pool/claim-random",
            headers=self._auth_headers(),
            json={
                "caller_id": "csrf-free-worker",
                "task_id": "csrf-free-task",
                "provider": "outlook",
            },
        )

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("code"), "OK")

    def test_external_pool_blueprint_applies_csrf_exempt_to_all_handlers(self):
        from outlook_web.routes import external_pool as external_pool_routes

        wrapped_handlers = []

        def fake_csrf_exempt(handler):
            wrapped_handlers.append(handler.__name__)
            return handler

        external_pool_routes.create_blueprint(csrf_exempt=fake_csrf_exempt)

        self.assertEqual(
            set(wrapped_handlers),
            {
                "api_external_pool_claim_random",
                "api_external_pool_claim_release",
                "api_external_pool_claim_complete",
                "api_external_pool_stats",
            },
        )

    def test_external_pool_claim_release_caller_mismatch(self):
        client = self.app.test_client()
        self._set_external_api_key("abc123")
        with self.app.app_context():
            from outlook_web.repositories import settings as settings_repo

            settings_repo.set_setting("pool_external_enabled", "true")
        self._insert_pool_account(provider="outlook")

        claim_resp = client.post(
            "/api/v1/external/pool/claim-random",
            headers=self._auth_headers(),
            json={
                "caller_id": "ext-worker-01",
                "task_id": "task-ext-002",
                "provider": "outlook",
            },
        )
        self.assertEqual(claim_resp.status_code, 200)
        claim_data = claim_resp.get_json()["data"]

        release_resp = client.post(
            "/api/v1/external/pool/claim-release",
            headers=self._auth_headers(),
            json={
                "account_id": claim_data["account_id"],
                "claim_token": claim_data["claim_token"],
                "caller_id": "ext-worker-02",
                "task_id": "task-ext-002",
            },
        )

        self.assertEqual(release_resp.status_code, 403)
        data = release_resp.get_json()
        self.assertFalse(data.get("success"))
        self.assertEqual(data.get("code"), "CALLER_MISMATCH")

    def test_external_pool_claim_complete_success(self):
        client = self.app.test_client()
        self._set_external_api_key("abc123")
        with self.app.app_context():
            from outlook_web.repositories import settings as settings_repo

            settings_repo.set_setting("pool_external_enabled", "true")
        self._insert_pool_account(provider="outlook")

        claim_resp = client.post(
            "/api/v1/external/pool/claim-random",
            headers=self._auth_headers(),
            json={
                "caller_id": "ext-worker-01",
                "task_id": "task-ext-complete",
                "provider": "outlook",
            },
        )
        self.assertEqual(claim_resp.status_code, 200)
        claim_data = claim_resp.get_json()["data"]

        complete_resp = client.post(
            "/api/v1/external/pool/claim-complete",
            headers=self._auth_headers(),
            json={
                "account_id": claim_data["account_id"],
                "claim_token": claim_data["claim_token"],
                "caller_id": "ext-worker-01",
                "task_id": "task-ext-complete",
                "result": "success",
                "detail": "done",
            },
        )

        self.assertEqual(complete_resp.status_code, 200)
        data = complete_resp.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("code"), "OK")
        self.assertEqual(data.get("data", {}).get("pool_status"), "used")

    def test_external_pool_stats_success(self):
        client = self.app.test_client()
        self._set_external_api_key("abc123")
        with self.app.app_context():
            from outlook_web.repositories import settings as settings_repo

            settings_repo.set_setting("pool_external_enabled", "true")
        self._insert_pool_account(pool_status="available")
        self._insert_pool_account(pool_status="used")

        resp = client.get("/api/v1/external/pool/stats", headers=self._auth_headers())

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("code"), "OK")
        pool_counts = data.get("data", {}).get("pool_counts", {})
        self.assertEqual(
            set(pool_counts.keys()),
            {"available", "claimed", "used", "cooldown", "frozen", "retired"},
        )

    def test_external_pool_stats_returns_feature_disabled_when_switch_off(self):
        client = self.app.test_client()
        self._set_external_api_key("abc123")

        resp = client.get("/api/v1/external/pool/stats", headers=self._auth_headers())

        self.assertEqual(resp.status_code, 403)
        data = resp.get_json()
        self.assertFalse(data.get("success"))
        self.assertEqual(data.get("code"), "FEATURE_DISABLED")

    def test_external_pool_stats_disabled_in_public_mode(self):
        client = self.app.test_client()
        self._set_external_api_key("abc123")
        with self.app.app_context():
            from outlook_web.repositories import settings as settings_repo

            settings_repo.set_setting("pool_external_enabled", "true")
        self._set_public_mode(True)
        self._set_ip_whitelist(["127.0.0.1"])
        self._set_disable_feature("external_api_disable_pool_stats", True)

        resp = client.get("/api/v1/external/pool/stats", headers=self._auth_headers())

        self.assertEqual(resp.status_code, 403)
        data = resp.get_json()
        self.assertEqual(data.get("code"), "FEATURE_DISABLED")
        self.assertEqual(data.get("data", {}).get("feature"), "pool_stats")

    def test_external_pool_claim_random_disabled_in_public_mode(self):
        client = self.app.test_client()
        self._set_external_api_key("abc123")
        with self.app.app_context():
            from outlook_web.repositories import settings as settings_repo

            settings_repo.set_setting("pool_external_enabled", "true")
        self._set_public_mode(True)
        self._set_ip_whitelist(["127.0.0.1"])
        self._set_disable_feature("external_api_disable_pool_claim_random", True)

        resp = client.post(
            "/api/v1/external/pool/claim-random",
            headers=self._auth_headers(),
            json={"caller_id": "ext-worker-01", "task_id": "task-ext-disabled"},
        )

        self.assertEqual(resp.status_code, 403)
        data = resp.get_json()
        self.assertEqual(data.get("code"), "FEATURE_DISABLED")
        self.assertEqual(data.get("data", {}).get("feature"), "pool_claim_random")

    def test_external_pool_claim_release_disabled_in_public_mode(self):
        client = self.app.test_client()
        self._set_external_api_key("abc123")
        with self.app.app_context():
            from outlook_web.repositories import settings as settings_repo

            settings_repo.set_setting("pool_external_enabled", "true")
        self._insert_pool_account(provider="outlook")
        claim_resp = client.post(
            "/api/v1/external/pool/claim-random",
            headers=self._auth_headers(),
            json={
                "caller_id": "ext-worker-01",
                "task_id": "task-ext-rel",
                "provider": "outlook",
            },
        )
        self.assertEqual(claim_resp.status_code, 200)
        claim_data = claim_resp.get_json()["data"]

        self._set_public_mode(True)
        self._set_ip_whitelist(["127.0.0.1"])
        self._set_disable_feature("external_api_disable_pool_claim_release", True)

        resp = client.post(
            "/api/v1/external/pool/claim-release",
            headers=self._auth_headers(),
            json={
                "account_id": claim_data["account_id"],
                "claim_token": claim_data["claim_token"],
                "caller_id": "ext-worker-01",
                "task_id": "task-ext-rel",
            },
        )

        self.assertEqual(resp.status_code, 403)
        data = resp.get_json()
        self.assertEqual(data.get("code"), "FEATURE_DISABLED")
        self.assertEqual(data.get("data", {}).get("feature"), "pool_claim_release")

    def test_external_pool_claim_complete_disabled_in_public_mode(self):
        client = self.app.test_client()
        self._set_external_api_key("abc123")
        with self.app.app_context():
            from outlook_web.repositories import settings as settings_repo

            settings_repo.set_setting("pool_external_enabled", "true")
        self._insert_pool_account(provider="outlook")
        claim_resp = client.post(
            "/api/v1/external/pool/claim-random",
            headers=self._auth_headers(),
            json={
                "caller_id": "ext-worker-01",
                "task_id": "task-ext-comp",
                "provider": "outlook",
            },
        )
        self.assertEqual(claim_resp.status_code, 200)
        claim_data = claim_resp.get_json()["data"]

        self._set_public_mode(True)
        self._set_ip_whitelist(["127.0.0.1"])
        self._set_disable_feature("external_api_disable_pool_claim_complete", True)

        resp = client.post(
            "/api/v1/external/pool/claim-complete",
            headers=self._auth_headers(),
            json={
                "account_id": claim_data["account_id"],
                "claim_token": claim_data["claim_token"],
                "caller_id": "ext-worker-01",
                "task_id": "task-ext-comp",
                "result": "success",
            },
        )

        self.assertEqual(resp.status_code, 403)
        data = resp.get_json()
        self.assertEqual(data.get("code"), "FEATURE_DISABLED")
        self.assertEqual(data.get("data", {}).get("feature"), "pool_claim_complete")

    def test_external_pool_requires_pool_access_for_multi_key(self):
        client = self.app.test_client()
        self._create_external_api_key("partner-a", "multi-pool-deny", pool_access=False)
        with self.app.app_context():
            from outlook_web.repositories import settings as settings_repo

            settings_repo.set_setting("pool_external_enabled", "true")
        self._insert_pool_account(provider="outlook")

        resp = client.get(
            "/api/v1/external/pool/stats",
            headers=self._auth_headers("multi-pool-deny"),
        )

        self.assertEqual(resp.status_code, 403)
        data = resp.get_json()
        self.assertEqual(data.get("code"), "FORBIDDEN")

    def test_external_pool_claim_random_requires_pool_access_for_multi_key(self):
        client = self.app.test_client()
        self._create_external_api_key("partner-a", "multi-pool-random-deny", pool_access=False)
        with self.app.app_context():
            from outlook_web.repositories import settings as settings_repo

            settings_repo.set_setting("pool_external_enabled", "true")
        self._insert_pool_account(provider="outlook")

        resp = client.post(
            "/api/v1/external/pool/claim-random",
            headers=self._auth_headers("multi-pool-random-deny"),
            json={
                "caller_id": "ext-worker-01",
                "task_id": "task-ext-no-access",
                "provider": "outlook",
            },
        )

        self.assertEqual(resp.status_code, 403)
        data = resp.get_json()
        self.assertEqual(data.get("code"), "FORBIDDEN")

    def test_external_pool_claim_release_requires_pool_access_for_multi_key(self):
        client = self.app.test_client()
        self._create_external_api_key("partner-deny", "multi-pool-release-deny", pool_access=False)
        self._create_external_api_key("partner-allow", "multi-pool-release-allow", pool_access=True)
        with self.app.app_context():
            from outlook_web.repositories import settings as settings_repo

            settings_repo.set_setting("pool_external_enabled", "true")
        self._insert_pool_account(provider="outlook")

        claim_resp = client.post(
            "/api/v1/external/pool/claim-random",
            headers=self._auth_headers("multi-pool-release-allow"),
            json={"caller_id": "ext-worker-01", "task_id": "release-deny", "provider": "outlook"},
        )
        self.assertEqual(claim_resp.status_code, 200)
        claim_data = claim_resp.get_json()["data"]

        resp = client.post(
            "/api/v1/external/pool/claim-release",
            headers=self._auth_headers("multi-pool-release-deny"),
            json={
                "account_id": claim_data["account_id"],
                "claim_token": claim_data["claim_token"],
                "caller_id": "ext-worker-01",
                "task_id": "release-deny",
            },
        )

        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.get_json().get("code"), "FORBIDDEN")

    def test_external_pool_claim_complete_requires_pool_access_for_multi_key(self):
        client = self.app.test_client()
        self._create_external_api_key("partner-deny", "multi-pool-complete-deny", pool_access=False)
        self._create_external_api_key("partner-allow", "multi-pool-complete-allow", pool_access=True)
        with self.app.app_context():
            from outlook_web.repositories import settings as settings_repo

            settings_repo.set_setting("pool_external_enabled", "true")
        self._insert_pool_account(provider="outlook")

        claim_resp = client.post(
            "/api/v1/external/pool/claim-random",
            headers=self._auth_headers("multi-pool-complete-allow"),
            json={"caller_id": "ext-worker-01", "task_id": "complete-deny", "provider": "outlook"},
        )
        self.assertEqual(claim_resp.status_code, 200)
        claim_data = claim_resp.get_json()["data"]

        resp = client.post(
            "/api/v1/external/pool/claim-complete",
            headers=self._auth_headers("multi-pool-complete-deny"),
            json={
                "account_id": claim_data["account_id"],
                "claim_token": claim_data["claim_token"],
                "caller_id": "ext-worker-01",
                "task_id": "complete-deny",
                "result": "success",
            },
        )

        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.get_json().get("code"), "FORBIDDEN")

    def test_external_pool_returns_api_key_not_configured(self):
        client = self.app.test_client()

        resp = client.get(
            "/api/v1/external/pool/stats",
            headers=self._auth_headers("unconfigured-key"),
        )

        self.assertEqual(resp.status_code, 403)
        data = resp.get_json()
        self.assertEqual(data.get("code"), "API_KEY_NOT_CONFIGURED")

    def test_external_pool_ip_not_allowed_in_public_mode(self):
        client = self.app.test_client()
        self._set_external_api_key("abc123")
        with self.app.app_context():
            from outlook_web.repositories import settings as settings_repo

            settings_repo.set_setting("pool_external_enabled", "true")
        self._set_public_mode(True)
        self._set_ip_whitelist(["10.0.0.1"])

        resp = client.get("/api/v1/external/pool/stats", headers=self._auth_headers())

        self.assertEqual(resp.status_code, 403)
        data = resp.get_json()
        self.assertEqual(data.get("code"), "IP_NOT_ALLOWED")

    def test_external_pool_allows_pool_access_for_multi_key(self):
        client = self.app.test_client()
        self._create_external_api_key("partner-a", "multi-pool-allow", pool_access=True)
        with self.app.app_context():
            from outlook_web.repositories import settings as settings_repo

            settings_repo.set_setting("pool_external_enabled", "true")
        self._insert_pool_account(provider="outlook")

        resp = client.get(
            "/api/v1/external/pool/stats",
            headers=self._auth_headers("multi-pool-allow"),
        )

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get("success"))
