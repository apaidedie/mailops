from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from examples.external_api_python_client import (
    CANONICAL_EXTERNAL_PREFIX,
    HttpResponse,
    MailOpsApiError,
    MailOpsClient,
    build_integration_bundle,
    main,
    summarize_integration_bundle_action_plan,
)


class FakeTransport:
    def __init__(
        self,
        responses: dict[tuple[str, str], dict],
        *,
        fail_on: tuple[str, str] | None = None,
        fail_status: int = 500,
        fail_code: str = "READ_FAILED",
    ) -> None:
        self.responses = responses
        self.fail_on = fail_on
        self.fail_status = fail_status
        self.fail_code = fail_code
        self.calls: list[tuple[str, str, str, dict | None, float]] = []

    def __call__(self, method: str, url: str, api_key: str, body: dict | None, timeout: float) -> HttpResponse:
        self.calls.append((method, url, api_key, body, timeout))
        key = (method, url)
        if self.fail_on == key:
            raise MailOpsApiError(
                "read failed",
                status=self.fail_status,
                code=self.fail_code,
                payload={"success": False, "code": self.fail_code},
            )
        payload = self.responses[key]
        return HttpResponse(status=200, payload=payload)


def _url(path: str) -> str:
    return f"https://mailbox.example.test{path}"


def _ok(data: dict) -> dict:
    return {"success": True, "code": "OK", "message": "success", "data": data}


def _discovery_responses() -> dict[tuple[str, str], dict]:
    endpoints = {
        "capabilities": f"{CANONICAL_EXTERNAL_PREFIX}/capabilities",
        "integration_bundle": f"{CANONICAL_EXTERNAL_PREFIX}/integration-bundle",
        "providers": f"{CANONICAL_EXTERNAL_PREFIX}/providers",
        "docs": f"{CANONICAL_EXTERNAL_PREFIX}/docs",
        "openapi": f"{CANONICAL_EXTERNAL_PREFIX}/openapi.json",
        "mailbox_session_start": f"{CANONICAL_EXTERNAL_PREFIX}/mailbox-sessions/start",
        "mailbox_session_read": f"{CANONICAL_EXTERNAL_PREFIX}/mailbox-sessions/read",
        "mailbox_session_close": f"{CANONICAL_EXTERNAL_PREFIX}/mailbox-sessions/close",
    }
    return {
        ("GET", _url(endpoints["capabilities"])): _ok(
            {
                "endpoints": endpoints,
                "documentation": {"entries": {"api_docs": {"endpoint": endpoints["docs"]}}},
                "integration_manifest": {
                    "auth": {"header": "X-API-Key", "placeholder": "<your-api-key>"},
                    "workflows": [
                        {
                            "key": "start_mailbox_session",
                            "label": "Start mailbox session",
                            "description": "Create a provider-neutral mailbox session.",
                        },
                        {"key": "browse_mailbox_directory", "label": "Browse mailbox directory"},
                    ],
                },
                "deployment_profile": {
                    "provider_values": {
                        "temp_apply": ["mail_tm", "duckmail"],
                        "pool_claim": ["auto", "imap", "mail_tm"],
                    },
                    "templates": {
                        "env": {
                            "format": "env",
                            "content": "TEMP_MAIL_PROVIDER=mail_tm\nDUCKMAIL_BEARER_TOKEN=\n",
                        },
                        "provider_config_json": {
                            "format": "json",
                            "content": '{\n  "providers": {\n    "temp_mail_provider": "mail_tm"\n  }\n}\n',
                        },
                        "provider_config_toml": {
                            "format": "toml",
                            "content": '[providers]\ntemp_mail_provider = "mail_tm"\n',
                        },
                    },
                    "config_file": {"priority_slot": "provider_config_file"},
                },
                "selection_policy": {"source_priority": ["env", "provider_config_file", "settings", "default"]},
            }
        ),
        ("GET", _url(endpoints["integration_bundle"])): _ok(_live_integration_bundle_data()),
        ("GET", _url(endpoints["providers"])): _ok(
            {
                "providers": [],
                "readiness_summary": {
                    "overall_status": "ready",
                    "totals": {"providers": 2, "ready_providers": 2},
                    "issues": {"needs_config": 0},
                },
            }
        ),
        ("GET", _url(endpoints["openapi"])): {"openapi": "3.1.0", "paths": {"/api/v1/external/capabilities": {}}},
    }


def _live_integration_bundle_data() -> dict:
    return {
        "version": 1,
        "service": "mailops",
        "status": "ready",
        "auth": {"header": "X-API-Key", "placeholder": "<your-api-key>"},
        "endpoints": {
            "integration_bundle": f"{CANONICAL_EXTERNAL_PREFIX}/integration-bundle",
            "openapi": f"{CANONICAL_EXTERNAL_PREFIX}/openapi.json",
        },
        "readiness": {
            "providers": {
                "overall_status": "ready",
                "totals": {"providers": 2, "ready_providers": 2},
                "issues": {"needs_config": 0},
            }
        },
        "openapi": {"version": "3.1.0", "path_count": 2},
        "action_plan": {
            "version": 1,
            "status": "ready",
            "summary": {"total": 2, "blocking": 0, "high": 1, "medium": 1, "low": 0},
            "items": [
                {
                    "key": "run_smoke_check",
                    "priority": "high",
                    "status": "ready",
                    "blocking": False,
                    "title": "Run smoke checker",
                    "command": "MAILOPS_API_KEY=<your-api-key> python scripts/external_api_smoke.py --base-url <your-base-url>",
                },
                {
                    "key": "start_mailbox_session",
                    "priority": "medium",
                    "status": "ready",
                    "blocking": False,
                    "title": "Start mailbox session",
                    "endpoint": f"{CANONICAL_EXTERNAL_PREFIX}/mailbox-sessions/start",
                },
            ],
        },
    }


class ExternalApiPythonClientTests(unittest.TestCase):
    def test_discover_reads_canonical_endpoints_and_caches_endpoint_map(self):
        transport = FakeTransport(_discovery_responses())
        client = MailOpsClient("https://mailbox.example.test", "test-key", transport=transport)

        data = client.discover()

        self.assertEqual(data["endpoints"]["mailbox_session_read"], f"{CANONICAL_EXTERNAL_PREFIX}/mailbox-sessions/read")
        self.assertEqual(client.endpoints["docs"], f"{CANONICAL_EXTERNAL_PREFIX}/docs")
        self.assertEqual(
            [call[1] for call in transport.calls],
            [
                _url(f"{CANONICAL_EXTERNAL_PREFIX}/capabilities"),
                _url(f"{CANONICAL_EXTERNAL_PREFIX}/providers"),
                _url(f"{CANONICAL_EXTERNAL_PREFIX}/openapi.json"),
            ],
        )

    def test_start_read_and_close_use_session_endpoints_and_expected_bodies(self):
        responses = _discovery_responses()
        responses[("POST", _url(f"{CANONICAL_EXTERNAL_PREFIX}/mailbox-sessions/start"))] = _ok(
            {
                "session_type": "pool_claim",
                "email": "user@example.test",
                "lifecycle": {"account_id": 7, "claim_token": "claim-demo"},
            }
        )
        responses[("POST", _url(f"{CANONICAL_EXTERNAL_PREFIX}/mailbox-sessions/read"))] = _ok(
            {"session_type": "pool_claim", "read_action": "verification_code", "result": {"verification_code": "123456"}}
        )
        responses[("POST", _url(f"{CANONICAL_EXTERNAL_PREFIX}/mailbox-sessions/close"))] = _ok(
            {"session_type": "pool_claim", "status": "closed"}
        )
        transport = FakeTransport(responses)
        client = MailOpsClient("https://mailbox.example.test", "test-key", transport=transport)
        client.discover()

        result = client.verification_flow(
            caller_id="registration-worker-1",
            task_id="signup-demo-1",
            provider="auto",
            provider_name="mail_tm",
        )

        self.assertEqual(result["verification"]["result"]["verification_code"], "123456")
        self.assertEqual(result["close"]["status"], "closed")
        post_bodies = [call[3] for call in transport.calls if call[0] == "POST"]
        self.assertEqual(post_bodies[0]["source_strategy"], "pool_first")
        self.assertEqual(post_bodies[0]["provider"], "auto")
        self.assertEqual(post_bodies[0]["provider_name"], "mail_tm")
        self.assertEqual(post_bodies[1]["read_action"], "verification_code")
        self.assertEqual(post_bodies[1]["claim_token"], "claim-demo")
        self.assertEqual(post_bodies[2]["account_id"], 7)
        self.assertEqual(post_bodies[2]["claim_token"], "claim-demo")

    def test_start_uses_canonical_fallback_without_discovery(self):
        responses = {
            ("POST", _url(f"{CANONICAL_EXTERNAL_PREFIX}/mailbox-sessions/start")): _ok(
                {"session_type": "task_temp_mailbox", "email": "temp@example.test", "lifecycle": {"task_token": "task-demo"}}
            )
        }
        transport = FakeTransport(responses)
        client = MailOpsClient("https://mailbox.example.test", "test-key", transport=transport)

        session = client.start_mailbox_session(caller_id="worker", task_id="task", source_strategy="task_temp_only")

        self.assertEqual(session["session_type"], "task_temp_mailbox")
        self.assertEqual(transport.calls[0][1], _url(f"{CANONICAL_EXTERNAL_PREFIX}/mailbox-sessions/start"))

    def test_verification_flow_closes_started_session_when_read_fails(self):
        responses = _discovery_responses()
        responses[("POST", _url(f"{CANONICAL_EXTERNAL_PREFIX}/mailbox-sessions/start"))] = _ok(
            {"session_type": "task_temp_mailbox", "email": "temp@example.test", "lifecycle": {"task_token": "task-demo"}}
        )
        responses[("POST", _url(f"{CANONICAL_EXTERNAL_PREFIX}/mailbox-sessions/close"))] = _ok(
            {"session_type": "task_temp_mailbox", "status": "closed"}
        )
        transport = FakeTransport(
            responses,
            fail_on=("POST", _url(f"{CANONICAL_EXTERNAL_PREFIX}/mailbox-sessions/read")),
        )
        client = MailOpsClient("https://mailbox.example.test", "test-key", transport=transport)
        client.discover()

        with self.assertRaises(MailOpsApiError):
            client.verification_flow(caller_id="worker", task_id="task", source_strategy="task_temp_only")

        close_calls = [call for call in transport.calls if call[1].endswith("/mailbox-sessions/close")]
        self.assertEqual(len(close_calls), 1)
        self.assertEqual(close_calls[0][3]["task_token"], "task-demo")

    def test_envelope_failure_raises_api_error(self):
        responses = {
            ("GET", _url(f"{CANONICAL_EXTERNAL_PREFIX}/capabilities")): {
                "success": False,
                "code": "FORBIDDEN",
                "message": "forbidden",
            }
        }
        client = MailOpsClient(
            "https://mailbox.example.test",
            "test-key",
            transport=FakeTransport(responses),
        )

        with self.assertRaises(MailOpsApiError) as ctx:
            client.get("capabilities")

        self.assertEqual(ctx.exception.code, "FORBIDDEN")
        self.assertEqual(ctx.exception.status, 200)

    def test_cli_discover_uses_api_key_from_environment(self):
        responses = _discovery_responses()
        transport = FakeTransport(responses)

        def build_client(base_url: str, api_key: str, *, timeout: float = 20.0):
            return MailOpsClient(base_url, api_key, timeout=timeout, transport=transport)

        with patch.dict(os.environ, {"MAILOPS_API_KEY": "env-key"}, clear=False):
            with patch("examples.external_api_python_client.MailOpsClient", side_effect=build_client):
                buffer = io.StringIO()
                with redirect_stdout(buffer):
                    exit_code = main(["--base-url", "https://mailbox.example.test", "discover"])

        self.assertEqual(exit_code, 0)
        self.assertIn('"openapi"', buffer.getvalue())
        self.assertTrue(all(call[2] == "env-key" for call in transport.calls))
        self.assertTrue(all(call[0] == "GET" for call in transport.calls))

    def test_build_integration_bundle_summarizes_live_discovery(self):
        transport = FakeTransport(_discovery_responses())
        client = MailOpsClient("https://mailbox.example.test", "test-key", transport=transport)

        bundle = build_integration_bundle("https://mailbox.example.test/", client.discover())

        self.assertEqual(bundle["base_url"], "https://mailbox.example.test")
        self.assertEqual(bundle["auth"], {"header": "X-API-Key", "placeholder": "<your-api-key>"})
        self.assertEqual(bundle["endpoints"]["mailbox_session_start"], f"{CANONICAL_EXTERNAL_PREFIX}/mailbox-sessions/start")
        self.assertEqual(bundle["documentation"]["entries"]["api_docs"]["endpoint"], f"{CANONICAL_EXTERNAL_PREFIX}/docs")
        self.assertEqual(
            bundle["provider_selection"]["source_priority"], ["env", "provider_config_file", "settings", "default"]
        )
        self.assertIn("duckmail", bundle["provider_selection"]["provider_values"]["temp_apply"])
        self.assertIn("provider_config_json", bundle["templates"])
        self.assertEqual(bundle["workflows"][0]["key"], "start_mailbox_session")
        self.assertEqual(bundle["readiness"]["overall_status"], "ready")
        self.assertEqual(bundle["openapi"], {"version": "3.1.0", "path_count": 1})

    def test_cli_integration_bundle_outputs_json_and_uses_only_readonly_discovery(self):
        responses = _discovery_responses()
        transport = FakeTransport(responses)

        def build_client(base_url: str, api_key: str, *, timeout: float = 20.0):
            return MailOpsClient(base_url, api_key, timeout=timeout, transport=transport)

        with patch("examples.external_api_python_client.MailOpsClient", side_effect=build_client):
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                exit_code = main(["--base-url", "https://mailbox.example.test", "--api-key", "test-key", "integration-bundle"])

        bundle = json.loads(buffer.getvalue())
        serialized = json.dumps(bundle, ensure_ascii=False)
        self.assertEqual(exit_code, 0)
        self.assertEqual(bundle["auth"]["placeholder"], "<your-api-key>")
        self.assertEqual(bundle["readiness"]["providers"]["totals"]["providers"], 2)
        self.assertNotIn("test-key", serialized)
        self.assertNotRegex(serialized, r"dk_[0-9a-fA-F]{20,}")
        self.assertEqual([call[0] for call in transport.calls], ["GET"])
        self.assertEqual([call[1] for call in transport.calls], [_url(f"{CANONICAL_EXTERNAL_PREFIX}/integration-bundle")])
        self.assertTrue(all("mailbox-sessions" not in call[1] for call in transport.calls))

    def test_action_plan_summary_projects_live_bundle_next_steps(self):
        summary = summarize_integration_bundle_action_plan(_live_integration_bundle_data())
        serialized = json.dumps(summary, ensure_ascii=False)

        self.assertEqual(summary["source"], "action_plan")
        self.assertEqual(summary["status"], "ready")
        self.assertEqual(summary["summary"], {"total": 2, "blocking": 0, "high": 1, "medium": 1, "low": 0})
        self.assertEqual(summary["blocking_keys"], [])
        self.assertEqual(summary["action_required_keys"], [])
        self.assertEqual(summary["ready_next_steps"], ["run_smoke_check", "start_mailbox_session"])
        self.assertIn("<your-api-key>", serialized)
        self.assertNotIn("test-key", serialized)
        self.assertNotRegex(serialized, r"dk_[0-9a-fA-F]{20,}")

    def test_action_plan_summary_redacts_secret_like_action_targets(self):
        bundle = _live_integration_bundle_data()
        bundle["action_plan"]["items"][0]["command"] = "curl -H 'Authorization: Bearer abcdefghijklmnopqrstuvwx'"

        summary = summarize_integration_bundle_action_plan(bundle)
        serialized = json.dumps(summary, ensure_ascii=False)

        self.assertTrue(summary["items"][0]["target_redacted"])
        self.assertNotIn("abcdefghijklmnopqrstuvwx", serialized)
        self.assertNotIn("Authorization: Bearer", serialized)

    def test_cli_integration_bundle_summary_outputs_action_plan_projection(self):
        responses = _discovery_responses()
        transport = FakeTransport(responses)

        def build_client(base_url: str, api_key: str, *, timeout: float = 20.0):
            return MailOpsClient(base_url, api_key, timeout=timeout, transport=transport)

        with patch("examples.external_api_python_client.MailOpsClient", side_effect=build_client):
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                exit_code = main(
                    ["--base-url", "https://mailbox.example.test", "--api-key", "test-key", "integration-bundle", "--summary"]
                )

        summary = json.loads(buffer.getvalue())
        serialized = json.dumps(summary, ensure_ascii=False)
        self.assertEqual(exit_code, 0)
        self.assertEqual(summary["source"], "action_plan")
        self.assertEqual(summary["ready_next_steps"], ["run_smoke_check", "start_mailbox_session"])
        self.assertNotIn("test-key", serialized)
        self.assertEqual([call[0] for call in transport.calls], ["GET"])
        self.assertEqual([call[1] for call in transport.calls], [_url(f"{CANONICAL_EXTERNAL_PREFIX}/integration-bundle")])
        self.assertTrue(all("mailbox-sessions" not in call[1] for call in transport.calls))

    def test_cli_integration_bundle_falls_back_to_local_discovery_for_older_service(self):
        responses = _discovery_responses()
        transport = FakeTransport(
            responses,
            fail_on=("GET", _url(f"{CANONICAL_EXTERNAL_PREFIX}/integration-bundle")),
            fail_status=404,
            fail_code="NOT_FOUND",
        )

        def build_client(base_url: str, api_key: str, *, timeout: float = 20.0):
            return MailOpsClient(base_url, api_key, timeout=timeout, transport=transport)

        with patch("examples.external_api_python_client.MailOpsClient", side_effect=build_client):
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                exit_code = main(["--base-url", "https://mailbox.example.test", "--api-key", "test-key", "integration-bundle"])

        bundle = json.loads(buffer.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(bundle["base_url"], "https://mailbox.example.test")
        self.assertEqual(bundle["readiness"]["totals"]["providers"], 2)
        self.assertEqual(
            [call[1] for call in transport.calls],
            [
                _url(f"{CANONICAL_EXTERNAL_PREFIX}/integration-bundle"),
                _url(f"{CANONICAL_EXTERNAL_PREFIX}/capabilities"),
                _url(f"{CANONICAL_EXTERNAL_PREFIX}/providers"),
                _url(f"{CANONICAL_EXTERNAL_PREFIX}/openapi.json"),
            ],
        )

    def test_action_plan_summary_handles_older_service_fallback_bundle(self):
        transport = FakeTransport(
            _discovery_responses(),
            fail_on=("GET", _url(f"{CANONICAL_EXTERNAL_PREFIX}/integration-bundle")),
            fail_status=404,
            fail_code="NOT_FOUND",
        )
        client = MailOpsClient("https://mailbox.example.test", "test-key", transport=transport)

        summary = summarize_integration_bundle_action_plan(client.integration_bundle())

        self.assertEqual(summary["source"], "fallback_readiness")
        self.assertEqual(summary["status"], "ready")
        self.assertEqual(summary["blocking_keys"], [])
        self.assertIn("start_mailbox_session", summary["ready_next_steps"])

    def test_cli_integration_bundle_summary_can_write_output_file(self):
        responses = _discovery_responses()
        transport = FakeTransport(responses)

        def build_client(base_url: str, api_key: str, *, timeout: float = 20.0):
            return MailOpsClient(base_url, api_key, timeout=timeout, transport=transport)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "integration-summary.json"
            with patch("examples.external_api_python_client.MailOpsClient", side_effect=build_client):
                buffer = io.StringIO()
                with redirect_stdout(buffer):
                    exit_code = main(
                        [
                            "--base-url",
                            "https://mailbox.example.test",
                            "--api-key",
                            "test-key",
                            "integration-bundle",
                            "--summary",
                            "--output",
                            str(output_path),
                        ]
                    )

            self.assertEqual(exit_code, 0)
            self.assertEqual(buffer.getvalue().strip(), str(output_path))
            summary = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(summary["source"], "action_plan")
        self.assertEqual(summary["summary"]["high"], 1)

    def test_cli_integration_bundle_can_write_output_file(self):
        responses = _discovery_responses()
        transport = FakeTransport(responses)

        def build_client(base_url: str, api_key: str, *, timeout: float = 20.0):
            return MailOpsClient(base_url, api_key, timeout=timeout, transport=transport)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "integration-bundle.json"
            with patch("examples.external_api_python_client.MailOpsClient", side_effect=build_client):
                buffer = io.StringIO()
                with redirect_stdout(buffer):
                    exit_code = main(
                        [
                            "--base-url",
                            "https://mailbox.example.test",
                            "--api-key",
                            "test-key",
                            "integration-bundle",
                            "--output",
                            str(output_path),
                        ]
                    )

            self.assertEqual(exit_code, 0)
            self.assertEqual(buffer.getvalue().strip(), str(output_path))
            bundle = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(bundle["endpoints"]["openapi"], f"{CANONICAL_EXTERNAL_PREFIX}/openapi.json")
        self.assertEqual([call[0] for call in transport.calls], ["GET"])

    def test_cli_verification_code_forwards_start_selection_fields(self):
        responses = _discovery_responses()
        responses[("POST", _url(f"{CANONICAL_EXTERNAL_PREFIX}/mailbox-sessions/start"))] = _ok(
            {"session_type": "task_temp_mailbox", "email": "temp@example.test", "lifecycle": {"task_token": "task-demo"}}
        )
        responses[("POST", _url(f"{CANONICAL_EXTERNAL_PREFIX}/mailbox-sessions/read"))] = _ok(
            {
                "session_type": "task_temp_mailbox",
                "read_action": "verification_code",
                "result": {"verification_code": "123456"},
            }
        )
        responses[("POST", _url(f"{CANONICAL_EXTERNAL_PREFIX}/mailbox-sessions/close"))] = _ok(
            {"session_type": "task_temp_mailbox", "status": "closed"}
        )
        transport = FakeTransport(responses)

        def build_client(base_url: str, api_key: str, *, timeout: float = 20.0):
            client = MailOpsClient(base_url, api_key, timeout=timeout, transport=transport)
            client.discover()
            return client

        with patch("examples.external_api_python_client.MailOpsClient", side_effect=build_client):
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                exit_code = main(
                    [
                        "--base-url",
                        "https://mailbox.example.test",
                        "--api-key",
                        "test-key",
                        "verification-code",
                        "--caller-id",
                        "registration-worker-1",
                        "--task-id",
                        "signup-demo-1",
                        "--source-strategy",
                        "task_temp_only",
                        "--provider",
                        "auto",
                        "--provider-name",
                        "mail_tm",
                        "--email-domain",
                        "example.test",
                        "--project-key",
                        "project-a",
                        "--prefix",
                        "signup",
                        "--domain",
                        "mail.example.test",
                        "--result",
                        "success",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn('"verification"', buffer.getvalue())
        start_body = next(call[3] for call in transport.calls if call[1].endswith("/mailbox-sessions/start"))
        self.assertEqual(start_body["source_strategy"], "task_temp_only")
        self.assertEqual(start_body["provider"], "auto")
        self.assertEqual(start_body["provider_name"], "mail_tm")
        self.assertEqual(start_body["email_domain"], "example.test")
        self.assertEqual(start_body["project_key"], "project-a")
        self.assertEqual(start_body["prefix"], "signup")
        self.assertEqual(start_body["domain"], "mail.example.test")

    def test_source_contains_only_placeholder_secrets(self):
        source = Path("examples/external_api_python_client.py").read_text(encoding="utf-8")

        self.assertIn("MAILOPS_API_KEY", source)
        self.assertNotRegex(source, r"dk_[0-9a-fA-F]{20,}")
        self.assertNotRegex(source, r"DUCKMAIL_BEARER_TOKEN\s*=")
        self.assertNotRegex(source, r"X-API-Key:\s+(?!<your-api-key>)[A-Za-z0-9_.-]{20,}")


if __name__ == "__main__":
    unittest.main()
