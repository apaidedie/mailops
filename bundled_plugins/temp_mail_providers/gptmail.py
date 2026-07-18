"""Official GPTMail temp-mail plugin (installable).

Registers both dual-register keys used by storage and operator UI:
``custom_domain_temp_mail`` and ``legacy_bridge``.
"""

from mailops.services.temp_mail_public_plugins import register_official_public_providers

register_official_public_providers(["gptmail"])
