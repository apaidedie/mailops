from __future__ import annotations

import importlib
import io
import json
import logging
import os
import unittest
from contextlib import redirect_stderr
from unittest.mock import patch

from flask import Flask, current_app, g

from mailops import config
from mailops.logging_config import JsonLogFormatter, configure_runtime_logging


class LoggingConfigTests(unittest.TestCase):
    def setUp(self):
        self.namespace_logger = logging.getLogger("mailops")
        self.namespace_handlers = list(self.namespace_logger.handlers)
        self.namespace_level = self.namespace_logger.level
        self.namespace_propagate = self.namespace_logger.propagate

    def tearDown(self):
        self.namespace_logger.handlers = self.namespace_handlers
        self.namespace_logger.setLevel(self.namespace_level)
        self.namespace_logger.propagate = self.namespace_propagate
        for key in ("LOG_FORMAT", "LOG_LEVEL", "PERF_LOGGING", "SECRET_KEY", "DATABASE_PATH", "SCHEDULER_AUTOSTART"):
            os.environ.pop(key, None)

    def test_log_config_defaults_and_perf_logging_compatibility(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(config.get_log_format(), "text")
            self.assertEqual(config.get_log_level(), "INFO")

        with patch.dict(os.environ, {"LOG_FORMAT": "JSON", "PERF_LOGGING": "true"}, clear=True):
            self.assertEqual(config.get_log_format(), "json")
            self.assertEqual(config.get_log_level(), "DEBUG")

        with patch.dict(os.environ, {"LOG_FORMAT": "xml", "LOG_LEVEL": "verbose", "PERF_LOGGING": "false"}, clear=True):
            self.assertEqual(config.get_log_format(), "text")
            self.assertEqual(config.get_log_level(), "INFO")

        with patch.dict(os.environ, {"LOG_LEVEL": "warning", "PERF_LOGGING": "true"}, clear=True):
            self.assertEqual(config.get_log_level(), "WARNING")

    def test_json_formatter_emits_stable_fields_and_safe_extras(self):
        record = logging.LogRecord(
            name="mailops.tests",
            level=logging.INFO,
            pathname=__file__,
            lineno=41,
            msg="mailbox refreshed",
            args=(),
            exc_info=None,
            func="test_json_formatter_emits_stable_fields_and_safe_extras",
        )
        record.event = "mailbox_refresh"
        record.status_code = 200
        record.duration_ms = 12.5
        record.provider = "mail_tm"
        record.secret_value = "must-not-render"

        payload = json.loads(JsonLogFormatter().format(record))

        for key in ("timestamp", "level", "logger", "message", "process", "thread", "module", "function", "line"):
            self.assertIn(key, payload)
        self.assertEqual(payload["level"], "INFO")
        self.assertEqual(payload["logger"], "mailops.tests")
        self.assertEqual(payload["message"], "mailbox refreshed")
        self.assertEqual(payload["event"], "mailbox_refresh")
        self.assertEqual(payload["status_code"], 200)
        self.assertEqual(payload["duration_ms"], 12.5)
        self.assertEqual(payload["provider"], "mail_tm")
        self.assertNotIn("secret_value", payload)
        self.assertTrue(payload["timestamp"].endswith("Z"))

    def test_json_formatter_adds_request_context_without_query_string(self):
        app = Flask(__name__)
        formatter = JsonLogFormatter()

        with app.test_request_context("/api/mailboxes?token=hidden", method="POST", environ_base={"REMOTE_ADDR": "127.0.0.1"}):
            g.trace_id = "trace-structured-123"
            record = logging.LogRecord("mailops.request", logging.INFO, __file__, 80, "request complete", (), None)
            payload = json.loads(formatter.format(record))

        self.assertEqual(payload["trace_id"], "trace-structured-123")
        self.assertEqual(payload["http_method"], "POST")
        self.assertEqual(payload["http_path"], "/api/mailboxes")
        self.assertEqual(payload["remote_addr"], "127.0.0.1")
        self.assertNotIn("token=hidden", json.dumps(payload))

    def test_json_formatter_serializes_exception_details(self):
        try:
            raise ValueError("structured boom")
        except ValueError:
            record = logging.LogRecord(
                "mailops.errors",
                logging.ERROR,
                __file__,
                99,
                "request failed",
                (),
                exc_info=__import__("sys").exc_info(),
            )

        payload = json.loads(JsonLogFormatter().format(record))

        self.assertEqual(payload["exception"]["type"], "ValueError")
        self.assertEqual(payload["exception"]["message"], "structured boom")
        self.assertIn("ValueError: structured boom", payload["exception"]["stack"])

    def test_runtime_configuration_replaces_only_managed_handler(self):
        app = Flask("mailops.logging-test")
        first_stream = io.StringIO()
        second_stream = io.StringIO()

        configure_runtime_logging(app, stream=first_stream, log_format="json", log_level="INFO")
        configure_runtime_logging(app, stream=second_stream, log_format="json", log_level="INFO")
        managed = [handler for handler in self.namespace_logger.handlers if getattr(handler, "_mailops_managed", False)]

        self.assertEqual(len(managed), 1)
        self.assertTrue(app.logger.propagate)
        app.logger.info("single line", extra={"event": "single_emit"})
        self.assertEqual(first_stream.getvalue(), "")
        lines = [line for line in second_stream.getvalue().splitlines() if line.strip()]
        self.assertEqual(len(lines), 1)
        self.assertEqual(json.loads(lines[0])["event"], "single_emit")

    def test_default_text_formatter_keeps_readable_legacy_shape(self):
        app = Flask("mailops.text-logging-test")
        stream = io.StringIO()

        configure_runtime_logging(app, stream=stream, log_format="text", log_level="INFO")
        app.logger.info("readable line")

        line = stream.getvalue().strip()
        self.assertRegex(line, r"^\d{2}:\d{2}:\d{2} mailops\.text-logging-test INFO readable line$")
        with self.assertRaises(json.JSONDecodeError):
            json.loads(line)

    def test_application_factory_emits_request_trace_in_json_mode(self):
        with patch.dict(
            os.environ,
            {
                "SECRET_KEY": "test-secret-key-for-structured-logging",
                "DATABASE_PATH": ":memory:",
                "SCHEDULER_AUTOSTART": "false",
                "LOG_FORMAT": "json",
                "LOG_LEVEL": "INFO",
            },
            clear=False,
        ):
            import mailops.app as app_module

            app_module._APP_INSTANCE = None
            app_module = importlib.reload(app_module)
            stream = io.StringIO()
            with redirect_stderr(stream):
                app = app_module.create_app(autostart_scheduler=False)

                @app.get("/_logging-contract")
                def logging_contract():
                    current_app.logger.info("request contract", extra={"event": "request_contract", "status_code": 200})
                    return {"ok": True}

                response = app.test_client().get("/_logging-contract?secret=hidden", headers={"X-Trace-Id": "trace-app-456"})

            app_module._APP_INSTANCE = None

        self.assertEqual(response.status_code, 200)
        payloads = []
        for line in stream.getvalue().splitlines():
            try:
                payloads.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        payload = next(item for item in payloads if item.get("event") == "request_contract")
        self.assertEqual(payload["trace_id"], response.headers["X-Trace-Id"])
        self.assertEqual(payload["http_method"], "GET")
        self.assertEqual(payload["http_path"], "/_logging-contract")
        self.assertNotIn("secret=hidden", json.dumps(payload))


if __name__ == "__main__":
    unittest.main()
