from __future__ import annotations

import os
import sqlite3
import time
from typing import Optional

from flask import g

from outlook_web import config
from outlook_web.errors import generate_trace_id, sanitize_error_details
from outlook_web.security.crypto import (
    encrypt_data,
    hash_password,
    is_encrypted,
    is_password_hashed,
)

# 数据库 Schema 版本（用于升级可验证/可诊断）
# v3：对齐 PRD-00005 / FD-00005 / TDD-00005（accounts 表新增多邮箱字段：account_type/provider/imap_host/imap_port/imap_password）
# v5：BUG-00011 P2 — Message-ID 去重防止重复推送
# v6：PRD-00008 P1 — 对外 API 限流表 + 公网模式默认配置
# v7：PRD-00008 P2 — wait-message 异步探测缓存表
# v8：PRD-00008 P1 — 上游真实探测结果缓存表
# v9：PRD-00008 P2 — 多 API Key 表
# v10：PRD-00008 P2 — 调用方日级使用统计表
# v11：PRD-00009 MT-1 — 邮箱池字段（pool_status/claimed_by/...）+ account_claim_logs 表 + pool settings
# v12：PRD-00009 P2 — external_api_keys 新增 pool_access 布尔权限
# v13：PRD-00010 V1.90 — 邮件通知设置 + 统一通知游标/投递日志表
# v14：PRD-00011 V1.91 — accounts 表新增简洁模式摘要字段，/api/accounts 只读持久化摘要
# v15：2026-03-26 临时邮箱能力正式化 — temp_emails 扩展字段、temp_email_messages 复合唯一、temp_mail_* 设置项
# v16：2026-03-28 patch — 修补 idx_temp_emails_task_token_unique 唯一索引（v15 旧库迁移代码未包含该索引，导致老库升级后缺失）
# v17：2026-04-02 project-scoped pool reuse — accounts 表新增 email_domain 列，account_project_usage 表（project_key 防同项目重复领取），external_probe_cache 表新增 baseline_timestamp 列
# v18：2026-04-09 CF临时邮箱接入邮箱池 — accounts 表新增 temp_mail_meta 列（JSON 格式存储 CF 邮箱元数据）
# v19：2026-04-10 提取器置信度门控（BUG-00017）
# v20：2026-04-10 验证码提取提速与 AI 增强（groups 表新增提取策略字段）
# v21：2026-04-11 Outlook OAuth 验证码提取渠道记忆（accounts.preferred_verification_channel）
# v22：2026-04-16 邮箱池项目维度成功复用（accounts.claimed_project_key + account_project_usage.success_*）
# v23：2026-04-19 数据概览大盘（verification_extract_logs + overview 兼容字段）
# v24：2026-07-01 临时邮箱接入邮箱池（temp_emails 新增池生命周期字段：pool_status/claimed_by/...，可被 claim-random 领取）

def migrate_sensitive_data(conn: sqlite3.Connection):
    """迁移现有明文敏感数据为加密数据。

    v22 改为通过 PRAGMA table_info 动态检测列是否存在，
    避免在早期 schema（如 v21 seed 数据中没有 password/refresh_token 列）上执行 SELECT 时报错。
    列名来自 SQLite 内置 PRAGMA 返回值，不存在 SQL 注入风险。
    """
    cursor = conn.cursor()
    account_columns = {row[1] for row in cursor.execute("PRAGMA table_info(accounts)").fetchall()}
    has_password = "password" in account_columns
    has_refresh_token = "refresh_token" in account_columns
    has_imap_password = "imap_password" in account_columns

    # 动态构建 SELECT，缺失列用 NULL AS 占位保持列数一致
    select_fields = ["id"]
    select_fields.append("password" if has_password else "NULL AS password")
    select_fields.append("refresh_token" if has_refresh_token else "NULL AS refresh_token")
    select_fields.append("imap_password" if has_imap_password else "NULL AS imap_password")
    cursor.execute(f"SELECT {', '.join(select_fields)} FROM accounts")
    accounts = cursor.fetchall()

    migrated_count = 0
    for account_id, password, refresh_token, imap_password in accounts:
        needs_update = False
        new_password = password
        new_refresh_token = refresh_token
        new_imap_password = imap_password

        # 检查并加密 password
        if password and not is_encrypted(password):
            new_password = encrypt_data(password)
            needs_update = True

        # 检查并加密 refresh_token
        if refresh_token and not is_encrypted(refresh_token):
            new_refresh_token = encrypt_data(refresh_token)
            needs_update = True

        # 检查并加密 imap_password
        if imap_password and not is_encrypted(imap_password):
            new_imap_password = encrypt_data(imap_password)
            needs_update = True

        # 更新数据库
        if needs_update:
            cursor.execute(
                """
                UPDATE accounts
                SET password = ?, refresh_token = ?, imap_password = ?
                WHERE id = ?
                """,
                (new_password, new_refresh_token, new_imap_password, account_id),
            )
            migrated_count += 1

    if migrated_count > 0:
        print(f"已迁移 {migrated_count} 个账号的敏感数据为加密存储")

    # 迁移 settings 表中明文存储的 provider 密钥
    _SETTINGS_SENSITIVE_KEYS = [
        "cf_worker_admin_key",
        "emailnator_api_key",
        "duckmail_bearer_token",
        "tempmail_lol_api_key",
        "temp_mail_lol_api_key",
    ]
    for key in _SETTINGS_SENSITIVE_KEYS:
        row = cursor.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        if row and row[0] and not is_encrypted(row[0]):
            encrypted_value = encrypt_data(row[0])
            cursor.execute(
                "UPDATE settings SET value = ?, updated_at = CURRENT_TIMESTAMP WHERE key = ?",
                (encrypted_value, key),
            )
            print(f"已迁移 settings.{key} 为加密存储")
