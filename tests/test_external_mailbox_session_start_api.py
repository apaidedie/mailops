from __future__ import annotations

import json
import unittest
import uuid
from unittest.mock import patch

from tests._import_app import clear_login_attempts, import_web_app_module

CANONICAL_EXTERNAL_PREFIX = "/api/v1/external"
LEGACY_EXTERNAL_PREFIX = "/api/external"


class ExternalMailboxSessionStartApiTests(unittest.TestCase):
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
            # Clear all claimable pool accounts so pool_first empty-pool fallback
            # is not polluted by leftover available rows from other tests.
            db.execute("DELETE FROM account_claim_logs")
            db.execute("DELETE FROM accounts")
            db.execute("DELETE FROM temp_email_messages WHERE email_address LIKE '%@session-start.test'")
            db.execute("DELETE FROM temp_emails WHERE email LIKE '%@session-start.test'")
            db.commit()
            settings_repo.set_setting("external_api_key", "session-key")
            settings_repo.set_setting("pool_external_enabled", "false")
            settings_repo.set_setting("pool_default_provider", "")
            settings_repo.set_setting("external_api_public_mode", "false")
            settings_repo.set_setting("external_api_ip_whitelist", "[]")
            settings_repo.set_setting("temp_mail_provider", "custom_domain_temp_mail")
            settings_repo.set_setting("temp_mail_domains", json.dumps(["session-start.test"]))
            settings_repo.set_setting("temp_mail_default_domain", "session-start.test")
            settings_repo.set_setting(
                "temp_mail_prefix_rules",
                '{"min_length":1,"max_length":32,"pattern":"^[a-z0-9][a-z0-9._-]*$"}',
            )

    @staticmethod
    def _auth_headers(value: str = "session-key") -> dict[str, str]:
        return {"X-API-Key": value}

    def _create_external_api_key(self, name: str, api_key: str, *, pool_access: bool = False):
        with self.app.app_context():
            from outlook_web.repositories import external_api_keys as external_api_keys_repo

            return external_api_keys_repo.create_external_api_key(
                name=name,
                api_key=api_key,
                allowed_emails=[],
                pool_access=pool_access,
            )

    def _insert_pool_account(self, *, provider: str = "outlook", account_type: str = "outlook") -> str:
        email_addr = f"{uuid.uuid4().hex}@session-start.test"
        with self.app.app_context():
            from outlook_web.db import get_db
            from outlook_web.repositories import settings as settings_repo

            settings_repo.set_setting("pool_external_enabled", "true")
            db = get_db()
            db.execute(
                """
                INSERT INTO accounts (
                    email, password, client_id, refresh_token,
                    group_id, status, account_type, provider, pool_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'available')
                """,
                (email_addr, "pw", "cid-test", "rt-test", 1, "active", account_type, provider),
            )
            db.commit()
        return email_addr

    @staticmethod
    def _task_mailbox_payload(prefix: str) -> dict:
        return {
            "email": f"{prefix}@session-start.test",
            "prefix": prefix,
            "domain": "session-start.test",
            "provider_name": "custom_domain_temp_mail",
            "provider_label": "Compatible Temp Mail Bridge",
            "read_capability": "temp_provider",
            "task_token": f"tmptask_{prefix}",
            "created_at": "2026-07-08T00:00:00Z",
            "status": "active",
        }

    def test_mailbox_session_start_claims_pool_mailbox_by_default(self):
        email_addr = self._insert_pool_account(provider="outlook")
        client = self.app.test_client()

        resp = client.post(
            "/api/v1/external/mailbox-sessions/start",
            headers=self._auth_headers(),
            json={"caller_id": "worker-1", "task_id": "job-pool", "provider": "outlook"},
        )

        self.assertEqual(resp.status_code, 200)
        payload = resp.get_json()["data"]
        self.assertEqual(payload["session_type"], "pool_claim")
        self.assertEqual(payload["email"], email_addr)
        self.assertEqual(payload["provider"], "outlook")
        self.assertEqual(payload["read_capability"], "graph")
        self.assertIn("claim_token", payload["lifecycle"])
        self.assertIn("account_id", payload["lifecycle"])
        self.assertEqual(
            payload["next_actions"]["read_verification_code"]["endpoint"], f"{CANONICAL_EXTERNAL_PREFIX}/verification-code"
        )
        self.assertEqual(
            payload["next_actions"]["complete_claim"]["endpoint"], f"{CANONICAL_EXTERNAL_PREFIX}/pool/claim-complete"
        )
        self.assertNotIn("password", json.dumps(payload).lower())
        self.assertNotIn("refresh_token", json.dumps(payload).lower())

    def test_mailbox_session_start_pool_first_falls_back_to_task_temp_when_pool_empty(self):
        with self.app.app_context():
            from outlook_web.repositories import settings as settings_repo

            settings_repo.set_setting("pool_external_enabled", "true")
        client = self.app.test_client()

        with patch(
            "outlook_web.controllers.external_temp_emails.temp_mail_service.apply_task_mailbox",
            return_value=self._task_mailbox_payload("fallback"),
        ):
            resp = client.post(
                "/api/v1/external/mailbox-sessions/start",
                headers=self._auth_headers(),
                json={
                    "caller_id": "worker-1",
                    "task_id": "job-fallback",
                    "source_strategy": "pool_first",
                    "provider_name": "custom_domain_temp_mail",
                    "prefix": "fallback",
                    "domain": "session-start.test",
                },
            )

        self.assertEqual(resp.status_code, 200)
        payload = resp.get_json()["data"]
        self.assertEqual(payload["session_type"], "task_temp_mailbox")
        self.assertEqual(payload["email"], "fallback@session-start.test")
        self.assertEqual(payload["provider"], "custom_domain_temp_mail")
        self.assertEqual(payload["read_capability"], "temp_provider")
        self.assertIn("task_token", payload["lifecycle"])
        self.assertEqual(
            payload["next_actions"]["finish_task_mailbox"]["endpoint"],
            f"{CANONICAL_EXTERNAL_PREFIX}/temp-emails/{{task_token}}/finish",
        )

    def test_mailbox_session_start_task_temp_only_allows_multi_key_without_pool_access(self):
        self._create_external_api_key("task-only", "task-only-key", pool_access=False)
        client = self.app.test_client()

        with patch(
            "outlook_web.controllers.external_temp_emails.temp_mail_service.apply_task_mailbox",
            return_value=self._task_mailbox_payload("taskonly"),
        ):
            resp = client.post(
                "/api/v1/external/mailbox-sessions/start",
                headers=self._auth_headers("task-only-key"),
                json={
                    "caller_id": "worker-1",
                    "task_id": "job-task-only",
                    "source_strategy": "task_temp_only",
                    "provider_name": "custom_domain_temp_mail",
                    "prefix": "taskonly",
                    "domain": "session-start.test",
                },
            )

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["data"]["session_type"], "task_temp_mailbox")

    def test_mailbox_session_start_rejects_pool_strategies_without_pool_access(self):
        self._create_external_api_key("no-pool", "no-pool-key", pool_access=False)
        client = self.app.test_client()

        for strategy in ("pool_first", "task_temp_first", "pool_only"):
            with self.subTest(strategy=strategy):
                resp = client.post(
                    "/api/v1/external/mailbox-sessions/start",
                    headers=self._auth_headers("no-pool-key"),
                    json={"caller_id": "worker-1", "task_id": f"job-{strategy}", "source_strategy": strategy},
                )
                self.assertEqual(resp.status_code, 403)
                self.assertEqual(resp.get_json()["code"], "FORBIDDEN")
                self.assertEqual(resp.get_json()["data"]["reason"], "pool_access_required")

    def test_mailbox_session_start_rejects_invalid_json_and_strategy_before_mutation(self):
        client = self.app.test_client()

        non_object = client.post(
            "/api/v1/external/mailbox-sessions/start",
            headers={**self._auth_headers(), "Content-Type": "application/json"},
            data="[]",
        )
        self.assertEqual(non_object.status_code, 400)
        self.assertEqual(non_object.get_json()["code"], "INVALID_PARAM")

        bad_strategy = client.post(
            "/api/v1/external/mailbox-sessions/start",
            headers=self._auth_headers(),
            json={"caller_id": "worker-1", "task_id": "job-invalid", "source_strategy": "unknown"},
        )
        self.assertEqual(bad_strategy.status_code, 400)
        self.assertEqual(bad_strategy.get_json()["code"], "INVALID_PARAM")

    def _start_pool_session(self, *, caller_id: str, task_id: str) -> dict:
        self._insert_pool_account(provider="outlook")
        client = self.app.test_client()
        resp = client.post(
            "/api/v1/external/mailbox-sessions/start",
            headers=self._auth_headers(),
            json={"caller_id": caller_id, "task_id": task_id, "provider": "outlook"},
        )
        self.assertEqual(resp.status_code, 200)
        return resp.get_json()["data"]

    def test_mailbox_session_close_completes_pool_claim(self):
        session = self._start_pool_session(caller_id="worker-1", task_id="job-close-complete")
        lifecycle = session["lifecycle"]
        client = self.app.test_client()

        resp = client.post(
            "/api/v1/external/mailbox-sessions/close",
            headers=self._auth_headers(),
            json={
                "session_type": "pool_claim",
                "account_id": lifecycle["account_id"],
                "claim_token": lifecycle["claim_token"],
                "caller_id": "worker-1",
                "task_id": "job-close-complete",
                "result": "success",
                "detail": "registration done",
            },
        )

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()["data"]
        self.assertEqual(data["session_type"], "pool_claim")
        self.assertEqual(data["close_action"], "complete_claim")
        self.assertEqual(data["status"], "closed")
        self.assertEqual(data["account_id"], lifecycle["account_id"])
        self.assertEqual(data["pool_status"], "used")
        payload_text = json.dumps(data, ensure_ascii=False).lower()
        for secret_field in ("password", "refresh_token", "provider_jwt", "api_key", "bearer"):
            self.assertNotIn(secret_field, payload_text)

    def test_mailbox_session_close_releases_pool_claim(self):
        session = self._start_pool_session(caller_id="worker-1", task_id="job-close-release")
        lifecycle = session["lifecycle"]
        client = self.app.test_client()

        resp = client.post(
            "/api/v1/external/mailbox-sessions/close",
            headers=self._auth_headers(),
            json={
                "session_type": "pool_claim",
                "account_id": lifecycle["account_id"],
                "claim_token": lifecycle["claim_token"],
                "caller_id": "worker-1",
                "task_id": "job-close-release",
                "result": "release",
                "reason": "retry later",
            },
        )

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()["data"]
        self.assertEqual(data["session_type"], "pool_claim")
        self.assertEqual(data["close_action"], "release_claim")
        self.assertEqual(data["status"], "closed")
        self.assertEqual(data["pool_status"], "available")

    def test_mailbox_session_close_finishes_task_temp_mailbox(self):
        with self.app.app_context():
            from outlook_web.repositories import temp_emails as temp_emails_repo

            temp_emails_repo.create_temp_email(
                email_addr="close-task@session-start.test",
                mailbox_type="task",
                visible_in_ui=False,
                source="custom_domain_temp_mail",
                prefix="close-task",
                domain="session-start.test",
                task_token="tmptask_session_close",
                consumer_key="legacy:settings.external_api_key",
                caller_id="worker-1",
                task_id="job-close-task",
            )

        client = self.app.test_client()
        resp = client.post(
            "/api/v1/external/mailbox-sessions/close",
            headers=self._auth_headers(),
            json={
                "session_type": "task_temp_mailbox",
                "task_token": "tmptask_session_close",
                "caller_id": "worker-1",
                "task_id": "job-close-task",
                "result": "success",
                "detail": "done",
            },
        )

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()["data"]
        self.assertEqual(data["session_type"], "task_temp_mailbox")
        self.assertEqual(data["close_action"], "finish_task_mailbox")
        self.assertEqual(data["status"], "closed")
        self.assertEqual(data["task_token"], "tmptask_session_close")
        self.assertEqual(data["email"], "close-task@session-start.test")

        with self.app.app_context():
            from outlook_web.repositories import temp_emails as temp_emails_repo

            mailbox = temp_emails_repo.get_temp_email_by_task_token("tmptask_session_close")
        self.assertEqual(mailbox["status"], "finished")

    def test_mailbox_session_close_rejects_invalid_json_and_session_type(self):
        client = self.app.test_client()

        non_object = client.post(
            "/api/v1/external/mailbox-sessions/close",
            headers={**self._auth_headers(), "Content-Type": "application/json"},
            data="[]",
        )
        self.assertEqual(non_object.status_code, 400)
        self.assertEqual(non_object.get_json()["code"], "INVALID_PARAM")

        bad_type = client.post(
            "/api/v1/external/mailbox-sessions/close",
            headers=self._auth_headers(),
            json={"session_type": "unknown", "caller_id": "worker-1", "task_id": "job-invalid"},
        )
        self.assertEqual(bad_type.status_code, 400)
        self.assertEqual(bad_type.get_json()["code"], "INVALID_PARAM")
        self.assertEqual(bad_type.get_json()["data"]["allowed_values"], ["pool_claim", "task_temp_mailbox"])

    def test_mailbox_session_close_rejects_pool_close_without_pool_access(self):
        self._create_external_api_key("pool-owner", "pool-owner-key", pool_access=True)
        self._create_external_api_key("no-pool", "no-pool-key", pool_access=False)
        self._insert_pool_account(provider="outlook")
        client = self.app.test_client()
        start_resp = client.post(
            "/api/v1/external/mailbox-sessions/start",
            headers=self._auth_headers("pool-owner-key"),
            json={"caller_id": "worker-1", "task_id": "job-no-pool", "provider": "outlook"},
        )
        self.assertEqual(start_resp.status_code, 200)
        lifecycle = start_resp.get_json()["data"]["lifecycle"]

        resp = client.post(
            "/api/v1/external/mailbox-sessions/close",
            headers=self._auth_headers("no-pool-key"),
            json={
                "session_type": "pool_claim",
                "account_id": lifecycle["account_id"],
                "claim_token": lifecycle["claim_token"],
                "caller_id": "worker-1",
                "task_id": "job-no-pool",
                "result": "success",
            },
        )

        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.get_json()["code"], "FORBIDDEN")
        self.assertEqual(resp.get_json()["data"]["reason"], "pool_access_required")

    def test_mailbox_session_close_respects_public_mode_pool_feature_disables(self):
        cases = [
            ("release", "external_api_disable_pool_claim_release", "pool_claim_release"),
            ("success", "external_api_disable_pool_claim_complete", "pool_claim_complete"),
        ]
        for result, setting_key, feature in cases:
            with self.subTest(feature=feature):
                session = self._start_pool_session(caller_id="worker-1", task_id=f"job-{feature}")
                lifecycle = session["lifecycle"]
                with self.app.app_context():
                    from outlook_web.repositories import settings as settings_repo

                    settings_repo.set_setting("external_api_public_mode", "true")
                    settings_repo.set_setting(setting_key, "true")
                client = self.app.test_client()

                resp = client.post(
                    "/api/v1/external/mailbox-sessions/close",
                    headers=self._auth_headers(),
                    json={
                        "session_type": "pool_claim",
                        "account_id": lifecycle["account_id"],
                        "claim_token": lifecycle["claim_token"],
                        "caller_id": "worker-1",
                        "task_id": f"job-{feature}",
                        "result": result,
                    },
                )

                self.assertEqual(resp.status_code, 403)
                self.assertEqual(resp.get_json()["code"], "FEATURE_DISABLED")
                self.assertEqual(resp.get_json()["data"]["feature"], feature)

                with self.app.app_context():
                    from outlook_web.repositories import settings as settings_repo

                    settings_repo.set_setting("external_api_public_mode", "false")
                    settings_repo.set_setting(setting_key, "false")

    def test_mailbox_session_close_rejects_invalid_pool_result_without_mutating_claim(self):
        session = self._start_pool_session(caller_id="worker-1", task_id="job-invalid-result")
        lifecycle = session["lifecycle"]
        client = self.app.test_client()

        resp = client.post(
            "/api/v1/external/mailbox-sessions/close",
            headers=self._auth_headers(),
            json={
                "session_type": "pool_claim",
                "account_id": lifecycle["account_id"],
                "claim_token": lifecycle["claim_token"],
                "caller_id": "worker-1",
                "task_id": "job-invalid-result",
                "result": "not_a_pool_result",
            },
        )

        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.get_json()["code"], "INVALID_RESULT")
        with self.app.app_context():
            from outlook_web.db import get_db

            row = (
                get_db()
                .execute(
                    "SELECT pool_status FROM accounts WHERE id = ?",
                    (lifecycle["account_id"],),
                )
                .fetchone()
            )
        self.assertEqual(row["pool_status"], "claimed")

    def test_mailbox_session_close_rejects_other_consumer_task_token(self):
        with self.app.app_context():
            from outlook_web.repositories import external_api_keys as external_api_keys_repo
            from outlook_web.repositories import temp_emails as temp_emails_repo

            owner = external_api_keys_repo.create_external_api_key(name="owner", api_key="owner-close-key")
            external_api_keys_repo.create_external_api_key(name="other", api_key="other-close-key")
            temp_emails_repo.create_temp_email(
                email_addr="owned-close@session-start.test",
                mailbox_type="task",
                visible_in_ui=False,
                source="custom_domain_temp_mail",
                prefix="owned-close",
                domain="session-start.test",
                task_token="tmptask_session_owned",
                consumer_key=owner["consumer_key"],
                caller_id="worker-1",
                task_id="job-owned-task",
            )

        client = self.app.test_client()
        resp = client.post(
            "/api/v1/external/mailbox-sessions/close",
            headers=self._auth_headers("other-close-key"),
            json={
                "session_type": "task_temp_mailbox",
                "task_token": "tmptask_session_owned",
                "caller_id": "worker-1",
                "task_id": "job-owned-task",
                "result": "success",
            },
        )

        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.get_json()["code"], "FORBIDDEN")

    @patch("outlook_web.controllers.external_temp_emails.external_api_service.list_messages_for_external")
    def test_mailbox_session_read_pool_claim_lists_messages_and_logs_read_context(self, mock_list_messages):
        session = self._start_pool_session(caller_id="worker-1", task_id="job-read-pool")
        lifecycle = session["lifecycle"]
        mock_list_messages.return_value = (
            [
                {
                    "id": "msg-new",
                    "email_address": session["email"],
                    "from_address": "noreply@example.com",
                    "subject": "Verification",
                    "content_preview": "Code 123456",
                    "timestamp": 4102444800,
                    "created_at": "2100-01-01T00:00:00Z",
                    "method": "Graph API",
                }
            ],
            "Graph API",
        )
        client = self.app.test_client()

        resp = client.post(
            "/api/v1/external/mailbox-sessions/read",
            headers=self._auth_headers(),
            json={
                "session_type": "pool_claim",
                "read_action": "messages",
                "caller_id": "worker-1",
                "task_id": "job-read-pool",
                "claim_token": lifecycle["claim_token"],
                "top": 5,
            },
        )

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()["data"]
        self.assertEqual(data["session_type"], "pool_claim")
        self.assertEqual(data["read_action"], "messages")
        self.assertEqual(data["email"], session["email"])
        self.assertEqual(data["result"]["count"], 1)
        self.assertEqual(data["result"]["emails"][0]["id"], "msg-new")
        self.assertNotIn("claim_token", json.dumps(data).lower())
        self.assertNotIn("refresh_token", json.dumps(data).lower())
        mock_list_messages.assert_called_once()

        with self.app.app_context():
            from outlook_web.db import get_db

            row = (
                get_db()
                .execute(
                    "SELECT caller_id, task_id, action, detail FROM account_claim_logs WHERE claim_token = ? AND action = 'read' ORDER BY id DESC LIMIT 1",
                    (lifecycle["claim_token"],),
                )
                .fetchone()
            )
        self.assertIsNotNone(row)
        self.assertEqual(row["caller_id"], "worker-1")
        self.assertEqual(row["task_id"], "job-read-pool")
        self.assertIn("session read_action=messages", row["detail"])

    @patch("outlook_web.controllers.external_temp_emails.external_api_service.get_verification_result")
    def test_mailbox_session_read_task_temp_verification_code(self, mock_get_verification):
        with self.app.app_context():
            from outlook_web.repositories import temp_emails as temp_emails_repo

            temp_emails_repo.create_temp_email(
                email_addr="read-task@session-start.test",
                mailbox_type="task",
                visible_in_ui=False,
                source="custom_domain_temp_mail",
                prefix="read-task",
                domain="session-start.test",
                task_token="tmptask_session_read",
                consumer_key="legacy:settings.external_api_key",
                caller_id="worker-1",
                task_id="job-read-task",
            )
        mock_get_verification.return_value = {
            "email": "read-task@session-start.test",
            "verification_code": "123456",
            "matched_email_id": "msg-code",
            "method": "Temp Mail",
        }
        client = self.app.test_client()

        resp = client.post(
            "/api/v1/external/mailbox-sessions/read",
            headers=self._auth_headers(),
            json={
                "session_type": "task_temp_mailbox",
                "read_action": "verification_code",
                "caller_id": "worker-1",
                "task_id": "job-read-task",
                "task_token": "tmptask_session_read",
            },
        )

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()["data"]
        self.assertEqual(data["session_type"], "task_temp_mailbox")
        self.assertEqual(data["read_action"], "verification_code")
        self.assertEqual(data["email"], "read-task@session-start.test")
        self.assertEqual(data["result"]["verification_code"], "123456")
        payload_text = json.dumps(data, ensure_ascii=False).lower()
        self.assertNotIn("task_token", payload_text)
        self.assertNotIn("consumer_key", payload_text)
        mock_get_verification.assert_called_once()

    def test_mailbox_session_read_rejects_other_consumer_task_token(self):
        with self.app.app_context():
            from outlook_web.repositories import external_api_keys as external_api_keys_repo
            from outlook_web.repositories import temp_emails as temp_emails_repo

            owner = external_api_keys_repo.create_external_api_key(name="owner-read", api_key="owner-read-key")
            external_api_keys_repo.create_external_api_key(name="other-read", api_key="other-read-key")
            temp_emails_repo.create_temp_email(
                email_addr="owned-read@session-start.test",
                mailbox_type="task",
                visible_in_ui=False,
                source="custom_domain_temp_mail",
                prefix="owned-read",
                domain="session-start.test",
                task_token="tmptask_session_read_owned",
                consumer_key=owner["consumer_key"],
                caller_id="worker-1",
                task_id="job-owned-read",
            )

        client = self.app.test_client()
        resp = client.post(
            "/api/v1/external/mailbox-sessions/read",
            headers=self._auth_headers("other-read-key"),
            json={
                "session_type": "task_temp_mailbox",
                "read_action": "latest_message",
                "caller_id": "worker-1",
                "task_id": "job-owned-read",
                "task_token": "tmptask_session_read_owned",
            },
        )

        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.get_json()["code"], "EMAIL_SCOPE_FORBIDDEN")

    def test_mailbox_session_read_rejects_invalid_json_and_action(self):
        client = self.app.test_client()

        non_object = client.post(
            "/api/v1/external/mailbox-sessions/read",
            headers={**self._auth_headers(), "Content-Type": "application/json"},
            data="[]",
        )
        self.assertEqual(non_object.status_code, 400)
        self.assertEqual(non_object.get_json()["code"], "INVALID_PARAM")

        bad_action = client.post(
            "/api/v1/external/mailbox-sessions/read",
            headers=self._auth_headers(),
            json={"session_type": "pool_claim", "read_action": "unknown", "caller_id": "worker-1", "task_id": "job-invalid"},
        )
        self.assertEqual(bad_action.status_code, 400)
        self.assertEqual(bad_action.get_json()["code"], "INVALID_PARAM")
        self.assertIn("verification_code", bad_action.get_json()["data"]["allowed_values"])

    @patch("outlook_web.controllers.external_temp_emails.external_api_service.get_message_detail_for_external")
    def test_mailbox_session_read_respects_public_mode_raw_disable_before_reading(self, mock_detail):
        session = self._start_pool_session(caller_id="worker-1", task_id="job-raw-disabled")
        lifecycle = session["lifecycle"]
        with self.app.app_context():
            from outlook_web.repositories import settings as settings_repo

            settings_repo.set_setting("external_api_public_mode", "true")
            settings_repo.set_setting("external_api_disable_raw_content", "true")
        client = self.app.test_client()

        resp = client.post(
            "/api/v1/external/mailbox-sessions/read",
            headers=self._auth_headers(),
            json={
                "session_type": "pool_claim",
                "read_action": "message_raw",
                "caller_id": "worker-1",
                "task_id": "job-raw-disabled",
                "claim_token": lifecycle["claim_token"],
                "message_id": "msg-raw",
            },
        )

        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.get_json()["code"], "FEATURE_DISABLED")
        self.assertEqual(resp.get_json()["data"]["feature"], "raw_content")
        mock_detail.assert_not_called()

    def test_mailbox_session_start_is_exposed_in_capabilities_and_openapi(self):
        client = self.app.test_client()

        capabilities_resp = client.get("/api/v1/external/capabilities", headers=self._auth_headers())
        self.assertEqual(capabilities_resp.status_code, 200)
        capabilities = capabilities_resp.get_json()["data"]
        self.assertEqual(
            capabilities["endpoints"]["mailbox_session_start"], f"{CANONICAL_EXTERNAL_PREFIX}/mailbox-sessions/start"
        )
        self.assertEqual(
            capabilities["endpoints"]["mailbox_session_read"], f"{CANONICAL_EXTERNAL_PREFIX}/mailbox-sessions/read"
        )
        self.assertEqual(
            capabilities["endpoints"]["mailbox_session_close"], f"{CANONICAL_EXTERNAL_PREFIX}/mailbox-sessions/close"
        )
        self.assertEqual(capabilities["legacy_endpoints"], {})
        self.assertFalse(capabilities["compatibility"]["legacy_supported"])
        self.assertIn("mailbox_session_start", capabilities["features"])
        self.assertIn("mailbox_session_read", capabilities["features"])
        self.assertIn("mailbox_session_close", capabilities["features"])
        self.assertEqual(
            capabilities["quickstart"]["endpoints"]["mailbox_session_start"],
            f"{CANONICAL_EXTERNAL_PREFIX}/mailbox-sessions/start",
        )
        self.assertEqual(
            capabilities["quickstart"]["endpoints"]["mailbox_session_read"],
            f"{CANONICAL_EXTERNAL_PREFIX}/mailbox-sessions/read",
        )
        self.assertEqual(
            capabilities["quickstart"]["endpoints"]["mailbox_session_close"],
            f"{CANONICAL_EXTERNAL_PREFIX}/mailbox-sessions/close",
        )
        self.assertEqual(
            capabilities["mailbox_session"]["read_endpoint"], f"{CANONICAL_EXTERNAL_PREFIX}/mailbox-sessions/read"
        )
        self.assertEqual(
            capabilities["mailbox_session"]["close_endpoint"], f"{CANONICAL_EXTERNAL_PREFIX}/mailbox-sessions/close"
        )
        self.assertIn("read_action", capabilities["mailbox_session"]["read_fields"])
        self.assertIn("verification_code", capabilities["mailbox_session"]["read_action_values"])
        self.assertIn("session_type", capabilities["mailbox_session"]["close_fields"])
        workflow_keys = {item["key"] for item in capabilities["integration_manifest"]["workflows"]}
        self.assertIn("start_mailbox_session", workflow_keys)
        start_workflow = next(
            item for item in capabilities["integration_manifest"]["workflows"] if item["key"] == "start_mailbox_session"
        )
        start_steps = {item["key"]: item for item in start_workflow["steps"]}
        self.assertEqual(start_steps["start_session"]["next"]["success"], "read_session")
        self.assertEqual(start_steps["read_session"]["endpoint"], f"{CANONICAL_EXTERNAL_PREFIX}/mailbox-sessions/read")
        self.assertEqual(start_steps["close_session"]["endpoint"], f"{CANONICAL_EXTERNAL_PREFIX}/mailbox-sessions/close")

        openapi_resp = client.get("/api/v1/external/openapi.json", headers=self._auth_headers())
        self.assertEqual(openapi_resp.status_code, 200)
        openapi = openapi_resp.get_json()
        self.assertIn(f"{CANONICAL_EXTERNAL_PREFIX}/mailbox-sessions/start", openapi["paths"])
        self.assertIn(f"{CANONICAL_EXTERNAL_PREFIX}/mailbox-sessions/read", openapi["paths"])
        self.assertIn(f"{CANONICAL_EXTERNAL_PREFIX}/mailbox-sessions/close", openapi["paths"])
        self.assertNotIn(f"{LEGACY_EXTERNAL_PREFIX}/mailbox-sessions/start", openapi["paths"])
        self.assertEqual(openapi.get("x-legacy-endpoints") or {}, {})
        operation = openapi["paths"][f"{CANONICAL_EXTERNAL_PREFIX}/mailbox-sessions/start"]["post"]
        self.assertEqual(operation["operationId"], "externalMailboxSessionStart")
        self.assertEqual(
            operation["requestBody"]["content"]["application/json"]["schema"]["$ref"],
            "#/components/schemas/MailboxSessionStartRequest",
        )
        schemas = openapi["components"]["schemas"]
        self.assertEqual(
            schemas["MailboxSessionStartRequest"]["properties"]["source_strategy"]["enum"],
            ["pool_first", "task_temp_first", "pool_only", "task_temp_only"],
        )
        self.assertIn("MailboxSessionData", schemas)
        read_operation = openapi["paths"][f"{CANONICAL_EXTERNAL_PREFIX}/mailbox-sessions/read"]["post"]
        self.assertEqual(read_operation["operationId"], "externalMailboxSessionRead")
        self.assertEqual(
            read_operation["requestBody"]["content"]["application/json"]["schema"]["$ref"],
            "#/components/schemas/MailboxSessionReadRequest",
        )
        self.assertIn("MailboxSessionReadRequest", schemas)
        self.assertIn("MailboxSessionReadData", schemas)
        self.assertIn("ProbeCreateData", schemas)
        self.assertEqual(
            schemas["MailboxSessionReadRequest"]["properties"]["read_action"]["enum"],
            [
                "messages",
                "latest_message",
                "message_detail",
                "message_raw",
                "verification_code",
                "verification_link",
                "wait_message",
            ],
        )
        close_operation = openapi["paths"][f"{CANONICAL_EXTERNAL_PREFIX}/mailbox-sessions/close"]["post"]
        self.assertEqual(close_operation["operationId"], "externalMailboxSessionClose")
        self.assertEqual(
            close_operation["requestBody"]["content"]["application/json"]["schema"]["$ref"],
            "#/components/schemas/MailboxSessionCloseRequest",
        )
        self.assertIn("MailboxSessionCloseRequest", schemas)
        self.assertIn("MailboxSessionCloseData", schemas)
        self.assertEqual(
            schemas["MailboxSessionCloseRequest"]["properties"]["session_type"]["enum"], ["pool_claim", "task_temp_mailbox"]
        )
        self.assertEqual(schemas["MailboxSessionCloseData"]["properties"]["status"]["enum"], ["closed"])
        schema_text = json.dumps(schemas["MailboxSessionData"], ensure_ascii=False).lower()
        schema_text += json.dumps(schemas["MailboxSessionReadData"], ensure_ascii=False).lower()
        schema_text += json.dumps(schemas["MailboxSessionCloseData"], ensure_ascii=False).lower()
        for secret_field in ("password", "refresh_token", "provider_jwt", "api_key", "bearer"):
            self.assertNotIn(secret_field, schema_text)


if __name__ == "__main__":
    unittest.main()
