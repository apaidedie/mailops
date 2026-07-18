from __future__ import annotations

import os
import sqlite3
import time
from typing import Optional

from flask import g

from mailops import config
from mailops.errors import generate_trace_id, sanitize_error_details
from mailops.security.crypto import (
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

DB_SCHEMA_VERSION = 24

DB_SCHEMA_VERSION_KEY = "db_schema_version"

DB_SCHEMA_LAST_UPGRADE_TRACE_ID_KEY = "db_schema_last_upgrade_trace_id"

DB_SCHEMA_LAST_UPGRADE_ERROR_KEY = "db_schema_last_upgrade_error"
