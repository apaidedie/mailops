from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from mailops.services import email_push


class EmailPushTransportModeTests(unittest.TestCase):
    def test_port_587_forces_starttls_and_disables_ssl_even_when_env_conflicts(self):
        with patch.dict(
            os.environ,
            {
                "EMAIL_NOTIFICATION_SMTP_HOST": "smtp.example.com",
                "EMAIL_NOTIFICATION_FROM": "noreply@example.com",
                "EMAIL_NOTIFICATION_SMTP_PORT": "587",
                "EMAIL_NOTIFICATION_SMTP_USE_SSL": "true",
                "EMAIL_NOTIFICATION_SMTP_USE_TLS": "false",
            },
            clear=False,
        ):
            cfg = email_push.get_email_push_service_config()

        self.assertEqual(cfg["port"], 587)
        self.assertTrue(cfg["use_tls"])
        self.assertFalse(cfg["use_ssl"])

    def test_port_465_forces_ssl_and_disables_starttls_even_when_env_conflicts(self):
        with patch.dict(
            os.environ,
            {
                "EMAIL_NOTIFICATION_SMTP_HOST": "smtp.example.com",
                "EMAIL_NOTIFICATION_FROM": "noreply@example.com",
                "EMAIL_NOTIFICATION_SMTP_PORT": "465",
                "EMAIL_NOTIFICATION_SMTP_USE_SSL": "false",
                "EMAIL_NOTIFICATION_SMTP_USE_TLS": "true",
            },
            clear=False,
        ):
            cfg = email_push.get_email_push_service_config()

        self.assertEqual(cfg["port"], 465)
        self.assertTrue(cfg["use_ssl"])
        self.assertFalse(cfg["use_tls"])

    def test_non_standard_port_with_both_enabled_prefers_ssl(self):
        with patch.dict(
            os.environ,
            {
                "EMAIL_NOTIFICATION_SMTP_HOST": "smtp.example.com",
                "EMAIL_NOTIFICATION_FROM": "noreply@example.com",
                "EMAIL_NOTIFICATION_SMTP_PORT": "2525",
                "EMAIL_NOTIFICATION_SMTP_USE_SSL": "true",
                "EMAIL_NOTIFICATION_SMTP_USE_TLS": "true",
            },
            clear=False,
        ):
            cfg = email_push.get_email_push_service_config()

        self.assertEqual(cfg["port"], 2525)
        self.assertTrue(cfg["use_ssl"])
        self.assertFalse(cfg["use_tls"])


if __name__ == "__main__":
    unittest.main()
