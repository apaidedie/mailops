"""Test bootstrap: keep official public temp providers registered for unit tests.

Production only loads Mail.tm / DuckMail / TempMail.lol / Emailnator after plugin
install. Tests still need the classes in the registry for existing coverage.
"""

from __future__ import annotations


def pytest_configure(config):  # noqa: ARG001
    try:
        from mailops.services.temp_mail_public_plugins import register_official_public_providers

        register_official_public_providers()
    except Exception:
        # Avoid hard-failing collection if app import order is incomplete.
        pass
