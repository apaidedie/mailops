from __future__ import annotations

import io
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from outlook_web.services.provider_catalog import (
    account_provider_label,
    temp_mail_provider_display_label,
)
from outlook_web.services.providers import (
    KNOWN_PROVIDER_KEYS,
    MAIL_PROVIDERS,
    PROVIDER_GROUP_NAME,
    get_provider_list,
    infer_provider_from_email,
)


def _parse_imap_port(value: Any) -> int | None:
    try:
        port = int((value or "").strip() if isinstance(value, str) else value)
    except Exception:
        return None
    return port if 1 <= port <= 65535 else None


def _looks_like_imap_host(value: str) -> bool:
    text = (value or "").strip().lower()
    return bool(text and "." in text and "@" not in text and " " not in text)


def _is_outlook_basic_auth_target(email_addr: str, host: str = "", provider_key: str = "") -> bool:
    inferred_provider = infer_provider_from_email(email_addr)
    normalized_host = (host or "").strip().lower()
    normalized_provider = (provider_key or "").strip().lower()
    return (
        inferred_provider == "outlook"
        or normalized_provider == "outlook"
        or normalized_host in {"outlook.live.com", "outlook.office365.com"}
    )


def _outlook_basic_auth_import_error() -> str:
    return "Outlook 邮箱不支持 IMAP Basic Auth 直连（包括 custom host 导入），请使用 4 段 OAuth 格式：邮箱----密码----client_id----refresh_token"


def _detect_line_type(
    line: str,
    fallback_host: str = "",
    fallback_port: int = 993,
) -> Dict[str, Any]:
    """
    根据分隔后的段数和内容特征，自动判断一行账号的类型。
    返回 {"type", "provider", "fields", "error", "auto_group_name"}。
    """
    parts = line.split("----")
    n = len(parts)

    def _err(msg: str) -> Dict[str, Any]:
        return {
            "type": "error",
            "provider": "",
            "fields": {},
            "error": msg,
            "auto_group_name": "",
        }

    # n >= 5 且 parts[2] == "custom" → 自定义 IMAP
    if n >= 5 and (parts[2] or "").strip().lower() == "custom":
        email = parts[0].strip()
        imap_pwd = parts[1].strip()
        host = (parts[3] or "").strip()
        raw_port = (parts[4] or "").strip()
        if not email or not imap_pwd or not host:
            return _err("custom 5段格式缺少必要字段")
        if not raw_port:
            return _err("custom 5段格式缺少 IMAP 端口")
        port = _parse_imap_port(raw_port)
        if port is None:
            return _err("custom IMAP 端口无效，应为 1-65535")
        if _is_outlook_basic_auth_target(email, host, "custom"):
            return _err(_outlook_basic_auth_import_error())
        return {
            "type": "imap",
            "provider": "custom",
            "fields": {
                "email": email,
                "imap_password": imap_pwd,
                "imap_host": host,
                "imap_port": port,
            },
            "error": None,
            "auto_group_name": PROVIDER_GROUP_NAME.get("custom", "自定义IMAP"),
        }

    if n == 4:
        email = parts[0].strip()
        imap_pwd = parts[1].strip()
        host = (parts[2] or "").strip()
        raw_port = (parts[3] or "").strip()
        if _looks_like_imap_host(host):
            if not email or not imap_pwd:
                return _err("4段格式缺少邮箱或密码")
            if not raw_port:
                return _err("custom 4段格式缺少 IMAP 端口")
            port = _parse_imap_port(raw_port)
            if port is None:
                return _err("custom IMAP 端口无效，应为 1-65535")
            if _is_outlook_basic_auth_target(email, host, "custom"):
                return _err(_outlook_basic_auth_import_error())
            return {
                "type": "imap",
                "provider": "custom",
                "fields": {
                    "email": email,
                    "imap_password": imap_pwd,
                    "imap_host": host,
                    "imap_port": port,
                },
                "error": None,
                "auto_group_name": PROVIDER_GROUP_NAME.get("custom", "自定义IMAP"),
            }

    # n >= 4 → Outlook（OAuth）
    if n >= 4:
        email = parts[0].strip()
        password = parts[1].strip()
        client_id = parts[2].strip()
        refresh_token = "----".join(parts[3:]).strip()
        if not email or not client_id or not refresh_token:
            return _err("Outlook 格式缺少 client_id 或 refresh_token")
        return {
            "type": "outlook",
            "provider": "outlook",
            "fields": {
                "email": email,
                "password": password,
                "client_id": client_id,
                "refresh_token": refresh_token,
            },
            "error": None,
            "auto_group_name": PROVIDER_GROUP_NAME.get("outlook", "Outlook"),
        }

    # n == 3 → 检查第3段是否为已知 provider
    if n == 3:
        email = parts[0].strip()
        imap_pwd = parts[1].strip()
        prov = (parts[2] or "").strip().lower()
        if not email or not imap_pwd:
            return _err("3段格式缺少邮箱或密码")
        if prov not in KNOWN_PROVIDER_KEYS:
            return _err(f"未知的 provider: {prov}")
        if prov == "outlook":
            return _err("Outlook 三段格式不支持密码直连，请使用 4 段 OAuth 格式：邮箱----密码----client_id----refresh_token")
        cfg = MAIL_PROVIDERS.get(prov, {})
        host = cfg.get("imap_host", "")
        port = int(cfg.get("imap_port", 993))
        if prov == "custom":
            return _err("3段格式不支持 custom（需要5段包含 host/port）")
        return {
            "type": "imap",
            "provider": prov,
            "fields": {
                "email": email,
                "imap_password": imap_pwd,
                "imap_host": host,
                "imap_port": port,
            },
            "error": None,
            "auto_group_name": PROVIDER_GROUP_NAME.get(prov, prov),
        }

    # n == 2 → 域名推断
    if n == 2:
        email = parts[0].strip()
        imap_pwd = parts[1].strip()
        if not email or not imap_pwd:
            return _err("2段格式缺少邮箱或密码")
        prov = infer_provider_from_email(email)
        if prov:
            if prov == "outlook":
                return _err(
                    "Outlook 两段格式不支持密码直连，请使用 4 段 OAuth 格式：邮箱----密码----client_id----refresh_token"
                )
            cfg = MAIL_PROVIDERS.get(prov, {})
            host = cfg.get("imap_host", "")
            port = int(cfg.get("imap_port", 993))
            return {
                "type": "imap",
                "provider": prov,
                "fields": {
                    "email": email,
                    "imap_password": imap_pwd,
                    "imap_host": host,
                    "imap_port": port,
                },
                "error": None,
                "auto_group_name": PROVIDER_GROUP_NAME.get(prov, prov),
            }
        # 推断失败 → custom 兜底
        if fallback_host:
            return {
                "type": "imap",
                "provider": "custom",
                "fields": {
                    "email": email,
                    "imap_password": imap_pwd,
                    "imap_host": fallback_host,
                    "imap_port": fallback_port,
                },
                "error": None,
                "auto_group_name": PROVIDER_GROUP_NAME.get("custom", "自定义IMAP"),
            }
        return _err("未知域名且未提供兜底 IMAP 服务器地址")

    # n == 1 → 临时邮箱
    if n == 1:
        email = parts[0].strip()
        if not email or "@" not in email:
            return _err("无法解析的行")
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            return _err("邮箱格式不正确")
        return {
            "type": "temp_mail",
            "provider": "temp_mail",
            "fields": {"email": email},
            "error": None,
            "auto_group_name": PROVIDER_GROUP_NAME.get("temp_mail", "临时邮箱"),
        }

    return _err("无法解析的行")


def _build_export_text(accounts: List[Dict[str, Any]], temp_emails: Optional[List[Dict]] = None) -> str:
    """构建导出文本 v2：头部元信息 + 分段 + 临时邮箱分段。"""
    outlook_lines: List[str] = []
    imap_groups: Dict[str, List[str]] = {}
    temp_mail_groups: Dict[tuple[str, str], List[str]] = {}
    temp_mail_seen: set[str] = set()

    def append_temp_mail_line(email: Any, provider_name: Any = None) -> None:
        email_addr = str(email or "").strip()
        if not email_addr or email_addr in temp_mail_seen:
            return
        provider_key = str(provider_name or "custom_domain_temp_mail").strip() or "custom_domain_temp_mail"
        label = temp_mail_provider_display_label(provider_key, locale="zh")
        temp_mail_groups.setdefault((provider_key, label), []).append(email_addr)
        temp_mail_seen.add(email_addr)

    for acc in accounts or []:
        atype = (acc.get("account_type") or "outlook").strip().lower()
        prov = (acc.get("provider") or "").strip().lower()

        # 兼容历史 provider，统一按临时邮箱导出
        if prov in {"gptmail", "temp_mail", "cloudflare_temp_mail"} or atype == "temp_mail":
            append_temp_mail_line(acc.get("email", ""), prov)
            continue

        if atype == "outlook":
            line = f"{acc.get('email', '')}----{acc.get('password', '')}----{acc.get('client_id', '')}----{acc.get('refresh_token', '')}"
            outlook_lines.append(line)
            continue

        provider = prov or "custom"
        imap_pwd = acc.get("imap_password", "") or ""
        if provider == "custom":
            line = f"{acc.get('email', '')}----{imap_pwd}----{provider}----{acc.get('imap_host', '') or ''}----{acc.get('imap_port', 993) or 993}"
        else:
            line = f"{acc.get('email', '')}----{imap_pwd}----{provider}"

        imap_groups.setdefault(provider, []).append(line)

    # 追加 temp_emails 中的临时邮箱
    for te in temp_emails or []:
        meta = te.get("meta") if isinstance(te.get("meta"), dict) else {}
        provider_name = te.get("provider_name") or te.get("provider") or meta.get("provider_name") or te.get("source")
        append_temp_mail_line(te.get("email", ""), provider_name)

    # 统计
    temp_mail_count = sum(len(v) for v in temp_mail_groups.values())
    total = len(outlook_lines) + sum(len(v) for v in imap_groups.values()) + temp_mail_count
    buf = io.StringIO()

    # 头部元信息
    buf.write("# ============================================\n")
    buf.write("# Outlook Email Plus — 账号导出\n")
    buf.write(f"# 导出时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    buf.write(f"# 账号总数：{total}\n")
    if outlook_lines:
        buf.write(f"#   Outlook：{len(outlook_lines)}\n")
    for prov_key, lines in imap_groups.items():
        label = account_provider_label(prov_key) or prov_key
        buf.write(f"#   {label}：{len(lines)}\n")
    if temp_mail_count:
        buf.write(f"#   临时邮箱：{temp_mail_count}\n")
    buf.write("# 格式版本：v2\n")
    buf.write("# ============================================\n")

    # Outlook 分段
    if outlook_lines:
        buf.write("\n# === Outlook 账号 ===\n")
        for line in outlook_lines:
            buf.write(line + "\n")

    # IMAP 分段（按 provider 排序）
    provider_order = [p.get("key") for p in get_provider_list() if p.get("key")]
    provider_order = [p for p in provider_order if p not in ("outlook", "auto")]
    appended = set()
    for provider in provider_order:
        lines = imap_groups.get(provider) or []
        if not lines:
            continue
        label = account_provider_label(provider) or provider
        buf.write(f"\n# === IMAP 账号（{label}）===\n")
        for line in lines:
            buf.write(line + "\n")
        appended.add(provider)

    for provider, lines in imap_groups.items():
        if provider in appended:
            continue
        label = account_provider_label(provider) or provider
        buf.write(f"\n# === IMAP 账号（{label}）===\n")
        for line in lines:
            buf.write(line + "\n")

    # 临时邮箱分段
    for (_provider_key, label), lines in temp_mail_groups.items():
        buf.write(f"\n# === 临时邮箱（{label}）===\n")
        for line in lines:
            buf.write(line + "\n")

    return buf.getvalue()
