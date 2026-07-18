"""Official temp-mail providers that ship as installable plugins.

Implementation classes live in ``temp_mail_provider_public`` / ``temp_mail_provider_custom``;
they are no longer auto-registered at import time (except Cloudflare). Installing the
matching plugin file (or calling ``register_official_public_providers`` in tests)
registers them into the runtime provider registry.
"""

from __future__ import annotations

from typing import Iterable

from mailops.services.temp_mail_provider_base import register_provider
from mailops.services.temp_mail_provider_custom import (
    CustomTempMailProvider,
    LegacyBridgeTempMailProvider,
)
from mailops.services.temp_mail_provider_public import (
    DuckMailTempMailProvider,
    EmailnatorTempMailProvider,
    MailTmTempMailProvider,
    TempMailLolProvider,
)

# Plugin package name "gptmail" registers both dual-register keys used by storage/UI.
GPTMAIL_PLUGIN_PROVIDER_NAMES = ("custom_domain_temp_mail", "legacy_bridge")

OFFICIAL_PUBLIC_PROVIDER_CLASSES = {
    "custom_domain_temp_mail": CustomTempMailProvider,
    "legacy_bridge": LegacyBridgeTempMailProvider,
    "mail_tm": MailTmTempMailProvider,
    "duckmail": DuckMailTempMailProvider,
    "tempmail_lol": TempMailLolProvider,
    "emailnator": EmailnatorTempMailProvider,
}

OFFICIAL_PUBLIC_PROVIDER_NAMES = frozenset(OFFICIAL_PUBLIC_PROVIDER_CLASSES)


def register_official_public_providers(names: Iterable[str] | None = None) -> list[str]:
    """Register one or more official public providers. Returns registered names."""
    raw = {str(item or "").strip() for item in (names or OFFICIAL_PUBLIC_PROVIDER_NAMES)}
    selected = set(raw)
    # Installing/selecting the gptmail plugin package enables both dual-register keys.
    if "gptmail" in selected or not names:
        selected.update(GPTMAIL_PLUGIN_PROVIDER_NAMES)
    registered: list[str] = []
    for name, cls in OFFICIAL_PUBLIC_PROVIDER_CLASSES.items():
        if name not in selected:
            continue
        register_provider(cls)
        registered.append(name)
    return registered
