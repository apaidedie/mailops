"""
邮箱池服务层（PRD-00009 MT-1）

职责：
- 输入校验（caller_id / task_id / lease_seconds / result / detail 长度）
- 读取 settings（在 Flask app_context 下用 get_db，或直接接受 conn）
- 调用 repositories/pool.py 的原子操作
- 将 repository 层的异常转换为业务错误码
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Optional

from outlook_web.db import create_sqlite_connection
from outlook_web.repositories import pool as pool_repo
from outlook_web.repositories import settings as settings_repo
from outlook_web.services.external_request_limits import (
    CALLER_ID_MAX_LEN,
    DETAIL_MAX_LEN,
    EMAIL_DOMAIN_MAX_LEN,
    PROJECT_KEY_MAX_LEN,
    REASON_MAX_LEN,
    TASK_ID_MAX_LEN,
)
from outlook_web.services.provider_catalog import (
    GPTMAIL_POOL_TEMP_PROVIDER_NAMES,
    GPTMAIL_RUNTIME_ALIASES,
    LEGACY_ACCOUNT_POOL_ALIASES,
    get_active_account_provider_names,
    get_active_temp_provider_names,
    get_mailbox_provider_catalog,
    is_mailbox_provider_active,
)
from outlook_web.services.temp_mail_provider_factory import TempMailProviderFactoryError, get_temp_mail_provider

logger = logging.getLogger(__name__)

VALID_RESULTS = set(pool_repo.RESULT_TO_POOL_STATUS.keys())

# CF 邮箱 complete 时需要删除远程邮箱的 result 值
CF_DELETE_ON_RESULTS = {"success", "credential_invalid"}

# 池接口的 provider 参数需要和 /api/v1/external/providers 暴露的 catalog 保持同源。
# 这里额外保留历史别名，避免旧调用方传 gptmail/imap 时被新 catalog 误伤。
_LEGACY_ACCOUNT_PROVIDER_NAMES = set(LEGACY_ACCOUNT_POOL_ALIASES)
_LEGACY_TEMP_PROVIDER_NAMES = set(GPTMAIL_RUNTIME_ALIASES)
_GPTMAIL_TEMP_PROVIDER_NAMES = set(GPTMAIL_POOL_TEMP_PROVIDER_NAMES)


@dataclass(frozen=True)
class _ProviderSelection:
    account_provider: Optional[str]
    account_provider_names: Optional[set[str]]
    temp_provider_names: Optional[set[str]]
    claim_accounts: bool
    claim_temp_mailboxes: bool
    create_cloudflare_when_empty: bool
    create_temp_provider_when_empty: Optional[str]


def _catalog_provider_names(kind: str) -> set[str]:
    normalized_kind = str(kind or "").strip().lower()
    return {
        str(item.get("provider") or "").strip().lower()
        for item in get_mailbox_provider_catalog(include_inactive=True)
        if item.get("kind") == normalized_kind and str(item.get("provider") or "").strip()
    }


def _catalog_account_provider_types() -> dict[str, str]:
    return {
        str(item.get("provider") or "").strip().lower(): str(item.get("account_type") or "").strip().lower()
        for item in get_mailbox_provider_catalog(include_inactive=True)
        if item.get("kind") == "account" and str(item.get("provider") or "").strip()
    }


def _active_account_provider_filter() -> set[str] | None:
    active_names = get_active_account_provider_names()
    if active_names is None:
        return None
    return {item for item in active_names if item and item != "auto"}


def _active_temp_provider_filter() -> set[str] | None:
    active_names = get_active_temp_provider_names()
    if active_names is None:
        return None
    return {item for item in active_names if item}


def _imap_account_provider_names() -> set[str]:
    return {name for name, account_type in _catalog_account_provider_types().items() if account_type == "imap"}


def _intersect_optional_provider_filter(values: set[str], active_values: set[str] | None) -> set[str]:
    if active_values is None:
        return values
    return values.intersection(active_values)


def _provider_is_active_for_request(provider: str, *, is_account_provider: bool, is_temp_provider: bool) -> bool:
    if not settings_repo.mailbox_provider_filter_is_active():
        return True
    if is_account_provider and is_mailbox_provider_active("account", provider):
        return True
    if is_temp_provider and is_mailbox_provider_active("temp", provider):
        return True
    if provider in GPTMAIL_RUNTIME_ALIASES:
        return bool((get_active_temp_provider_names() or set()).intersection(GPTMAIL_POOL_TEMP_PROVIDER_NAMES))
    if provider == "imap":
        return bool(_imap_account_provider_names().intersection(get_active_account_provider_names() or set()))
    return False


def _temp_provider_names_for_request(provider: str) -> set[str]:
    if provider in {"custom", "gptmail", "temp_mail", "legacy_gptmail"}:
        return set(_GPTMAIL_TEMP_PROVIDER_NAMES)
    return {provider}


def _valid_provider_names() -> set[str]:
    return (
        _catalog_provider_names("account")
        | _catalog_provider_names("temp")
        | _LEGACY_ACCOUNT_PROVIDER_NAMES
        | _LEGACY_TEMP_PROVIDER_NAMES
    )


def _resolve_provider_selection(provider: Optional[str]) -> _ProviderSelection:
    """校验并解析 claim-random 的 provider 选择语义。"""
    if provider is None:
        default_provider = settings_repo.get_pool_default_provider()
        if default_provider:
            return _resolve_provider_selection(default_provider)
        active_account_names = _active_account_provider_filter()
        active_temp_names = _active_temp_provider_filter()
        return _ProviderSelection(
            account_provider=None,
            account_provider_names=active_account_names,
            temp_provider_names=active_temp_names,
            claim_accounts=active_account_names is None or bool(active_account_names),
            claim_temp_mailboxes=active_temp_names is None or bool(active_temp_names),
            create_cloudflare_when_empty=False,
            create_temp_provider_when_empty=None,
        )

    p = str(provider or "").strip().lower()
    if not p or p == "auto":
        active_account_names = _active_account_provider_filter()
        active_temp_names = _active_temp_provider_filter()
        return _ProviderSelection(
            account_provider=None,
            account_provider_names=active_account_names,
            temp_provider_names=active_temp_names,
            claim_accounts=active_account_names is None or bool(active_account_names),
            claim_temp_mailboxes=active_temp_names is None or bool(active_temp_names),
            create_cloudflare_when_empty=False,
            create_temp_provider_when_empty=None,
        )

    account_provider_names = _catalog_provider_names("account") | _LEGACY_ACCOUNT_PROVIDER_NAMES
    temp_provider_names = _catalog_provider_names("temp") | _LEGACY_TEMP_PROVIDER_NAMES
    if p not in account_provider_names and p not in temp_provider_names:
        raise PoolServiceError(
            f"provider 必须是 {sorted(_valid_provider_names())} 之一，或留空",
            "invalid_provider",
        )

    is_account_provider = p in account_provider_names
    is_temp_provider = p in temp_provider_names
    if not _provider_is_active_for_request(p, is_account_provider=is_account_provider, is_temp_provider=is_temp_provider):
        raise PoolServiceError(
            f"provider 未启用: {p}",
            "provider_not_active",
        )
    claim_temp_mailboxes = is_temp_provider or p == "custom"
    account_provider_names_for_request: set[str] | None = None
    if p == "imap":
        account_provider_names_for_request = _intersect_optional_provider_filter(
            _imap_account_provider_names(),
            _active_account_provider_filter(),
        )
    account_provider = p if (is_account_provider and p != "imap") or p in {"cloudflare_temp_mail", "gptmail"} else None
    temp_names_for_request = _temp_provider_names_for_request(p) if claim_temp_mailboxes else None
    if temp_names_for_request is not None:
        temp_names_for_request = _intersect_optional_provider_filter(temp_names_for_request, _active_temp_provider_filter())
    create_temp_provider_when_empty = None
    if claim_temp_mailboxes and temp_names_for_request and len(temp_names_for_request) == 1:
        requested_temp_provider = next(iter(temp_names_for_request))
        if requested_temp_provider != "cloudflare_temp_mail":
            create_temp_provider_when_empty = requested_temp_provider
    return _ProviderSelection(
        account_provider=account_provider,
        account_provider_names=account_provider_names_for_request,
        temp_provider_names=temp_names_for_request,
        claim_accounts=account_provider is not None or bool(account_provider_names_for_request),
        claim_temp_mailboxes=claim_temp_mailboxes and (temp_names_for_request is None or bool(temp_names_for_request)),
        create_cloudflare_when_empty=p == "cloudflare_temp_mail",
        create_temp_provider_when_empty=create_temp_provider_when_empty,
    )


class PoolServiceError(Exception):
    """业务错误，包含 HTTP 状态码和错误码。"""

    def __init__(self, message: str, error_code: str, http_status: int = 400):
        super().__init__(message)
        self.error_code = error_code
        self.http_status = http_status


def _validate_caller_id(caller_id: str) -> None:
    if not caller_id or not caller_id.strip():
        raise PoolServiceError("caller_id 不能为空", "caller_id_empty")
    if len(caller_id) > CALLER_ID_MAX_LEN:
        raise PoolServiceError(f"caller_id 超过最大长度 {CALLER_ID_MAX_LEN}", "caller_id_too_long")


def _validate_task_id(task_id: str) -> None:
    if not task_id or not task_id.strip():
        raise PoolServiceError("task_id 不能为空", "task_id_empty")
    if len(task_id) > TASK_ID_MAX_LEN:
        raise PoolServiceError(f"task_id 超过最大长度 {TASK_ID_MAX_LEN}", "task_id_too_long")


def _validate_lease_seconds(lease_seconds: int, max_lease: int = 3600) -> None:
    if lease_seconds <= 0:
        raise PoolServiceError("lease_seconds 必须大于 0", "lease_seconds_invalid")
    if lease_seconds > max_lease:
        raise PoolServiceError(f"lease_seconds 不能超过 {max_lease} 秒", "lease_seconds_too_large")


def _validate_project_key(project_key: Optional[str]) -> Optional[str]:
    if project_key is None:
        return None
    pk = project_key.strip()
    if not pk:
        return None
    if len(pk) > PROJECT_KEY_MAX_LEN:
        raise PoolServiceError(f"project_key 超过最大长度 {PROJECT_KEY_MAX_LEN}", "project_key_too_long")
    return pk


def _validate_email_domain(email_domain: Optional[str]) -> Optional[str]:
    if email_domain is None:
        return None
    d = email_domain.strip().lower()
    if not d:
        return None
    if len(d) > EMAIL_DOMAIN_MAX_LEN:
        raise PoolServiceError(f"email_domain 超过最大长度 {EMAIL_DOMAIN_MAX_LEN}", "email_domain_too_long")
    return d


def _read_settings_via_conn(conn) -> dict:
    """在独立连接场景下直接从 settings 表读取池相关配置。"""
    rows = conn.execute(
        "SELECT key, value FROM settings WHERE key IN (?, ?)",
        ("pool_cooldown_seconds", "pool_default_lease_seconds"),
    ).fetchall()
    result = {"pool_cooldown_seconds": 86400, "pool_default_lease_seconds": 600}
    for row in rows:
        try:
            result[row["key"]] = int(row["value"])
        except (TypeError, ValueError):
            pass
    return result


def _is_project_reuse_eligible_account(
    *,
    provider: Optional[str],
    account_type: Optional[str],
    claimed_project_key: Optional[str],
) -> bool:
    """判定账号是否适用项目维度成功复用路径 (FD §2.1)。

    三重门控缺一不可：
    1. claimed_project_key 非空 — 必须在 claim 时显式传入
    2. 非 cloudflare_temp_mail — CF 临时邮箱不在本期覆盖范围
    3. 非 temp_mail — 一次性临时邮箱不在本期覆盖范围
    """
    if not claimed_project_key:
        return False
    if (provider or "").strip() == "cloudflare_temp_mail":
        return False
    if (account_type or "").strip() == "temp_mail":
        return False
    return True


def claim_random(
    *,
    caller_id: str,
    task_id: str,
    provider: Optional[str] = None,
    project_key: Optional[str] = None,
    email_domain: Optional[str] = None,
) -> dict:
    _validate_caller_id(caller_id)
    _validate_task_id(task_id)
    provider_selection = _resolve_provider_selection(provider)
    project_key = _validate_project_key(project_key)
    email_domain = _validate_email_domain(email_domain)

    conn = create_sqlite_connection()
    try:
        settings = _read_settings_via_conn(conn)
        default_lease = settings["pool_default_lease_seconds"]
        _validate_lease_seconds(default_lease)

        if provider_selection.claim_accounts:
            try:
                account = pool_repo.claim_atomic(
                    conn,
                    caller_id=caller_id,
                    task_id=task_id,
                    lease_seconds=default_lease,
                    provider=provider_selection.account_provider,
                    provider_names=provider_selection.account_provider_names,
                    project_key=project_key,
                    email_domain=email_domain,
                )
            except pool_repo.PoolRepositoryError as e:
                # 将 Repository 层异常转换为 Service 层异常
                raise PoolServiceError(str(e), e.error_code, http_status=500) from e

            if account is not None:
                return account

        # accounts 池无命中：对临时邮箱类 provider 回退到 temp_emails 池领取。
        # 显式指定 provider 时按 provider_name 精确过滤；未指定时不限临时邮箱来源。
        if provider_selection.claim_temp_mailboxes:
            try:
                temp_account = pool_repo.claim_temp_mailbox_atomic(
                    conn,
                    caller_id=caller_id,
                    task_id=task_id,
                    lease_seconds=default_lease,
                    email_domain=email_domain,
                    provider_names=provider_selection.temp_provider_names,
                )
            except pool_repo.PoolRepositoryError as e:
                raise PoolServiceError(str(e), e.error_code, http_status=500) from e
            if temp_account is not None:
                return temp_account

        # CF 兼容旧路径：动态创建后仍写入 accounts，保留原删除与审计语义。
        if provider_selection.create_cloudflare_when_empty:
            created_email, created_meta = _create_cf_mailbox_for_pool(email_domain=email_domain)

            try:
                inserted = pool_repo.insert_claimed_account(
                    conn,
                    email=created_email,
                    caller_id=caller_id,
                    task_id=task_id,
                    lease_seconds=default_lease,
                    provider="cloudflare_temp_mail",
                    account_type="temp_mail",
                    project_key=project_key,
                    temp_mail_meta=created_meta,
                    claim_log_detail="CF邮箱动态创建",
                )
                return inserted
            except pool_repo.PoolRepositoryError as e:
                # DB 写入失败时，尽力删除已创建的远程邮箱，避免资源泄漏（非阻塞）
                _delete_cf_mailbox_nonblocking(email=created_email, meta=created_meta)
                raise PoolServiceError(str(e), e.error_code, http_status=500) from e
            except Exception as e:
                _delete_cf_mailbox_nonblocking(email=created_email, meta=created_meta)
                raise PoolServiceError("动态写入 CF 邮箱失败", "db_error", http_status=500) from e

        # 非 CF 临时邮箱 provider 写入 temp_emails，沿用统一临时邮箱读取链路。
        if provider_selection.create_temp_provider_when_empty:
            created_email, created_meta, temp_provider = _create_temp_provider_mailbox_for_pool(
                provider_name=provider_selection.create_temp_provider_when_empty,
                email_domain=email_domain,
            )
            try:
                return pool_repo.insert_claimed_temp_mailbox(
                    conn,
                    email=created_email,
                    caller_id=caller_id,
                    task_id=task_id,
                    lease_seconds=default_lease,
                    provider_name=provider_selection.create_temp_provider_when_empty,
                    meta=created_meta,
                    visible_in_ui=False,
                )
            except pool_repo.PoolRepositoryError as e:
                _delete_temp_provider_mailbox_nonblocking(
                    provider=temp_provider,
                    email=created_email,
                    meta=created_meta,
                )
                raise PoolServiceError(str(e), e.error_code, http_status=500) from e
            except Exception as e:
                _delete_temp_provider_mailbox_nonblocking(
                    provider=temp_provider,
                    email=created_email,
                    meta=created_meta,
                )
                raise PoolServiceError("动态写入临时邮箱失败", "db_error", http_status=500) from e

        raise PoolServiceError("池中没有符合条件的可用邮箱", "no_available_account", http_status=200)
    finally:
        conn.close()


def _validate_claim_ownership(
    row: Optional[dict],
    *,
    action: str,
    claim_token: str,
    caller_id: str,
    task_id: str,
) -> None:
    """校验 release/complete 的领取归属（accounts 与 temp_emails 共用）。"""
    if row is None:
        raise PoolServiceError("账号不存在", "account_not_found", http_status=400)
    if row.get("pool_status") != "claimed":
        raise PoolServiceError(
            f"账号当前状态为 '{row.get('pool_status')}'，无法 {action}",
            "not_claimed",
            http_status=409,
        )
    if row.get("claim_token") != claim_token:
        raise PoolServiceError("claim_token 不匹配", "token_mismatch", http_status=403)
    if row.get("claimed_by") != f"{caller_id}:{task_id}":
        raise PoolServiceError(
            "caller_id 或 task_id 与领取记录不一致",
            "caller_mismatch",
            http_status=403,
        )


def release_claim(
    *,
    account_id: int,
    claim_token: str,
    caller_id: str,
    task_id: str,
    reason: Optional[str] = None,
) -> None:
    """释放已领取的邮箱账号（不计入成功/失败统计，直接回 available）。"""
    _validate_caller_id(caller_id)
    _validate_task_id(task_id)
    if not claim_token or not claim_token.strip():
        raise PoolServiceError("claim_token 不能为空", "claim_token_empty")
    if reason and len(reason) > REASON_MAX_LEN:
        raise PoolServiceError(f"reason 超过最大长度 {REASON_MAX_LEN}", "reason_too_long")

    conn = create_sqlite_connection()
    try:
        # 临时邮箱池账号：account_id 带偏移，路由到 temp_emails
        if pool_repo.is_temp_pool_account_id(account_id):
            temp_id = pool_repo.temp_id_from_account_id(account_id)
            temp_row = pool_repo.get_temp_mailbox_pool_row(conn, temp_id)
            _validate_claim_ownership(
                temp_row, action="release", claim_token=claim_token, caller_id=caller_id, task_id=task_id
            )
            pool_repo.release_temp_mailbox(conn, temp_id, claim_token, caller_id, task_id, reason)
            return

        row = conn.execute(
            "SELECT id, claim_token, claimed_by, pool_status FROM accounts WHERE id = ?",
            (account_id,),
        ).fetchone()
        _validate_claim_ownership(
            dict(row) if row is not None else None,
            action="release",
            claim_token=claim_token,
            caller_id=caller_id,
            task_id=task_id,
        )

        pool_repo.release(conn, account_id, claim_token, caller_id, task_id, reason)
    finally:
        conn.close()


def complete_claim(
    *,
    account_id: int,
    claim_token: str,
    caller_id: str,
    task_id: str,
    result: str,
    detail: Optional[str] = None,
) -> str:
    """
    标记领取结果并驱动状态机流转。

    返回账号的新 pool_status。
    """
    _validate_caller_id(caller_id)
    _validate_task_id(task_id)
    if not claim_token or not claim_token.strip():
        raise PoolServiceError("claim_token 不能为空", "claim_token_empty")
    if result not in VALID_RESULTS:
        raise PoolServiceError(
            f"result 必须是 {sorted(VALID_RESULTS)} 之一",
            "invalid_result",
        )
    if detail and len(detail) > DETAIL_MAX_LEN:
        raise PoolServiceError(f"detail 超过最大长度 {DETAIL_MAX_LEN}", "detail_too_long")

    conn = create_sqlite_connection()
    try:
        # 临时邮箱池账号：account_id 带偏移，路由到 temp_emails（一次性资源，无项目复用/CF 删除）
        if pool_repo.is_temp_pool_account_id(account_id):
            temp_id = pool_repo.temp_id_from_account_id(account_id)
            temp_row = pool_repo.get_temp_mailbox_pool_row(conn, temp_id)
            _validate_claim_ownership(
                temp_row, action="complete", claim_token=claim_token, caller_id=caller_id, task_id=task_id
            )
            return pool_repo.complete_temp_mailbox(conn, temp_id, claim_token, caller_id, task_id, result, detail)

        row = conn.execute(
            """
            SELECT id, email, provider, account_type, temp_mail_meta,
                   claimed_project_key,
                   claim_token, claimed_by, pool_status
            FROM accounts
            WHERE id = ?
            """,
            (account_id,),
        ).fetchone()
        _validate_claim_ownership(
            dict(row) if row is not None else None,
            action="complete",
            claim_token=claim_token,
            caller_id=caller_id,
            task_id=task_id,
        )

        # 从 claim 上下文读取 claimed_project_key，而非依赖 API 入参
        # 保证 claim-complete 即使未传 project_key 也能正确判定复用路径（TDD §4.1 N-03）
        claimed_project_key = str(row["claimed_project_key"] or "").strip() or None
        enable_project_reuse = _is_project_reuse_eligible_account(
            provider=row["provider"],
            account_type=row["account_type"],
            claimed_project_key=claimed_project_key,
        )

        # complete 先更新本地状态（事务内），再做 CF 删除（非阻塞）
        new_status = pool_repo.complete(
            conn,
            account_id,
            claim_token,
            caller_id,
            task_id,
            result,
            detail,
            claimed_project_key=claimed_project_key,
            enable_project_reuse=enable_project_reuse,
        )

        if (row["provider"] or "").strip() == "cloudflare_temp_mail" and result in CF_DELETE_ON_RESULTS:
            meta_str = row["temp_mail_meta"]
            meta_obj = {}
            if isinstance(meta_str, str) and meta_str.strip():
                try:
                    meta_obj = json.loads(meta_str)
                except Exception:
                    meta_obj = {}
            _delete_cf_mailbox_nonblocking(email=row["email"], meta=meta_obj)

        return new_status
    finally:
        conn.close()


def _create_cf_mailbox_for_pool(*, email_domain: Optional[str]) -> tuple[str, dict]:
    """调用 CF Worker 创建邮箱（Service 层），返回 (email, meta_dict)。"""
    try:
        from outlook_web.services.temp_mail_provider_cf import (
            CloudflareTempMailProvider,
        )

        provider = CloudflareTempMailProvider()
        result = provider.create_mailbox(prefix=None, domain=email_domain)
    except Exception as e:
        # 上游异常：统一映射为 UPSTREAM_SERVER_ERROR
        logger.warning("[pool] CF create_mailbox exception: %s", e)
        raise PoolServiceError("CF Worker 创建邮箱异常", "UPSTREAM_SERVER_ERROR", http_status=500) from e

    if not isinstance(result, dict):
        raise PoolServiceError("CF Worker 返回格式错误", "UPSTREAM_BAD_PAYLOAD", http_status=500)

    if not result.get("success"):
        error_code = str(result.get("error_code") or "UPSTREAM_SERVER_ERROR")
        error_msg = str(result.get("error") or "CF Worker 创建邮箱失败")
        raise PoolServiceError(error_msg, error_code, http_status=500)

    email = str(result.get("email") or "").strip()
    if not email:
        raise PoolServiceError("CF Worker 未返回邮箱地址", "UPSTREAM_BAD_PAYLOAD", http_status=500)

    meta = result.get("meta") or {}
    if isinstance(meta, str):
        try:
            meta = json.loads(meta)
        except Exception:
            meta = {}

    if not isinstance(meta, dict):
        meta = {}

    if not _email_matches_requested_domain(email, email_domain):
        _delete_cf_mailbox_nonblocking(email=email, meta=meta)
        raise PoolServiceError("CF Worker 返回域名不匹配", "UPSTREAM_BAD_PAYLOAD", http_status=500)

    return email, meta


def _normalize_temp_provider_meta(result: dict, provider_name: str) -> dict:
    meta = result.get("meta") or {}
    if isinstance(meta, str):
        try:
            meta = json.loads(meta)
        except Exception:
            meta = {}
    if not isinstance(meta, dict):
        meta = {}
    meta["provider_name"] = str(result.get("provider_name") or provider_name).strip() or provider_name
    return meta


def _email_matches_requested_domain(email: str, requested_domain: Optional[str]) -> bool:
    if not requested_domain:
        return True
    if "@" not in email:
        return False
    return email.rsplit("@", 1)[1].strip().lower() == requested_domain.strip().lower()


def _create_temp_provider_mailbox_for_pool(*, provider_name: str, email_domain: Optional[str]) -> tuple[str, dict, object]:
    try:
        provider = get_temp_mail_provider(provider_name)
    except TempMailProviderFactoryError as e:
        raise PoolServiceError(e.message, e.code, http_status=e.status) from e
    except Exception as e:
        logger.warning("[pool] temp provider init exception: provider=%s, error=%s", provider_name, e)
        raise PoolServiceError("临时邮箱 Provider 初始化异常", "TEMP_MAIL_PROVIDER_INVALID", http_status=503) from e

    try:
        result = provider.create_mailbox(prefix=None, domain=email_domain)
    except Exception as e:
        logger.warning("[pool] temp provider create_mailbox exception: provider=%s, error=%s", provider_name, e)
        raise PoolServiceError("临时邮箱创建异常", "UPSTREAM_SERVER_ERROR", http_status=502) from e

    if not isinstance(result, dict):
        raise PoolServiceError("临时邮箱 Provider 返回格式错误", "UPSTREAM_BAD_PAYLOAD", http_status=502)

    if not result.get("success"):
        error_code = str(result.get("error_code") or "TEMP_EMAIL_CREATE_FAILED")
        error_msg = str(result.get("error") or "临时邮箱创建失败")
        raise PoolServiceError(error_msg, error_code, http_status=502)

    email = str(result.get("email") or "").strip()
    if not email:
        raise PoolServiceError("临时邮箱 Provider 未返回邮箱地址", "UPSTREAM_BAD_PAYLOAD", http_status=502)

    meta = _normalize_temp_provider_meta(result, provider_name)
    if not _email_matches_requested_domain(email, email_domain):
        _delete_temp_provider_mailbox_nonblocking(provider=provider, email=email, meta=meta)
        raise PoolServiceError("临时邮箱 Provider 返回域名不匹配", "UPSTREAM_BAD_PAYLOAD", http_status=502)

    return email, meta, provider


def _delete_temp_provider_mailbox_nonblocking(*, provider: object, email: str, meta: dict) -> None:
    try:
        delete_mailbox = getattr(provider, "delete_mailbox", None)
        if not callable(delete_mailbox):
            return
        success = delete_mailbox({"email": email, "meta": meta})
        if success:
            logger.info("[pool] 已删除远程临时邮箱: %s", email)
        else:
            logger.warning("[pool] 删除远程临时邮箱失败(返回 False): %s", email)
    except Exception as e:
        logger.warning("[pool] 删除远程临时邮箱异常: %s, error=%s", email, e)


def _delete_cf_mailbox_nonblocking(*, email: str, meta: dict) -> None:
    """非阻塞删除远程 CF 邮箱（仅记录日志，不抛异常）。"""
    try:
        from outlook_web.services.temp_mail_provider_cf import (
            CloudflareTempMailProvider,
        )

        provider = CloudflareTempMailProvider()
        success = provider.delete_mailbox({"email": email, "meta": meta})
        if success:
            logger.info("[pool] 已删除 CF 远程邮箱: %s", email)
        else:
            logger.warning("[pool] 删除 CF 远程邮箱失败(返回 False): %s", email)
    except Exception as e:
        logger.warning("[pool] 删除 CF 远程邮箱异常: %s, error=%s", email, e)


def get_claim_context(*, claim_token: str) -> Optional[dict]:
    """
    根据 claim_token 查询领取上下文（email / claimed_at / email_domain 等）。
    返回 dict 或 None（token 不存在时）。
    """
    if not claim_token or not claim_token.strip():
        return None
    conn = create_sqlite_connection()
    try:
        return pool_repo.get_claim_context(conn, claim_token.strip())
    finally:
        conn.close()


def append_claim_read_context(
    *,
    account_id: int,
    claim_token: str,
    caller_id: str,
    task_id: str,
    detail: Optional[str] = None,
) -> None:
    """
    追加一条读取上下文日志（claim 邮箱被用于邮件读取时记录）。
    """
    if not claim_token or not claim_token.strip():
        return
    # 临时邮箱池账号不写 account_claim_logs（该表 account_id 对 accounts 有外键约束）
    if pool_repo.is_temp_pool_account_id(account_id):
        return
    conn = create_sqlite_connection()
    try:
        pool_repo.append_claim_read_context(conn, account_id, claim_token, caller_id, task_id, detail)
    finally:
        conn.close()


def get_pool_stats() -> dict:
    """返回池状态统计（不修改任何数据）。"""
    conn = create_sqlite_connection()
    try:
        return pool_repo.get_stats(conn)
    finally:
        conn.close()
