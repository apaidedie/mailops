"""Official TempMail.lol temp-mail plugin (installable)."""

from mailops.services.temp_mail_public_plugins import register_official_public_providers

register_official_public_providers(["tempmail_lol"])
