from __future__ import annotations

import argparse
import io
import json
import os
import sqlite3
import sys
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

DEFAULT_DB_PATH = REPO_ROOT / "output" / "demo" / "mailops-demo.db"
DEMO_SECRET_KEY = "demo-local-secret-key-32bytes-minimum-0000000000000000"
DEMO_LOGIN_PASSWORD = "demo-admin-123"
DEMO_GROUP_NAME = "Demo Workspace"
DEMO_OPERATOR = "demo-seed"
DEMO_ACCOUNT_EMAILS = (
    "graph.orders@demo.local",
    "imap.signup@demo.local",
    "pool.reserve@demo.local",
)
DEMO_TEMP_EMAILS = (
    "duck.demo@temp.demo.local",
    "lol.demo@temp.demo.local",
    "nator.demo@mail.example",
    "worker.demo@temp.demo.local",
)
DEMO_CONSUMER_KEYS = ("demo-webhook", "demo-browser-extension", "demo-ci-worker")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sqlite_ts(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S")


def _resolve_db_path(value: str | None) -> Path:
    if not value:
        return DEFAULT_DB_PATH
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = (REPO_ROOT / path).resolve()
    return path


def _startup_command(db_path: Path) -> str:
    return f'$env:DATABASE_PATH="{db_path}"; $env:SCHEDULER_AUTOSTART="false"; python web_mailops_app.py'


def _demo_plan(db_path: Path) -> dict[str, Any]:
    return {
        "database_path": str(db_path),
        "default_database": str(DEFAULT_DB_PATH),
        "login_password": DEMO_LOGIN_PASSWORD,
        "startup_command": _startup_command(db_path),
        "planned_rows": {
            "accounts": len(DEMO_ACCOUNT_EMAILS),
            "temp_emails": len(DEMO_TEMP_EMAILS),
            "temp_email_messages": 6,
            "verification_extract_logs": 8,
            "external_api_consumer_usage_daily": 9,
            "account_claim_logs": 3,
            "account_project_usage": 2,
        },
    }


def _set_demo_env(db_path: Path) -> None:
    os.environ.setdefault("SECRET_KEY", DEMO_SECRET_KEY)
    os.environ.setdefault("LOGIN_PASSWORD", DEMO_LOGIN_PASSWORD)
    os.environ.setdefault("SCHEDULER_AUTOSTART", "false")
    os.environ["DATABASE_PATH"] = str(db_path)


def _remove_sqlite_files(db_path: Path) -> None:
    for path in (db_path, Path(str(db_path) + "-wal"), Path(str(db_path) + "-shm")):
        if path.exists():
            path.unlink()


def _delete_demo_rows(conn: sqlite3.Connection) -> None:
    account_ids = [
        int(row["id"])
        for row in conn.execute(
            "SELECT id FROM accounts WHERE email IN (?, ?, ?)",
            DEMO_ACCOUNT_EMAILS,
        ).fetchall()
    ]
    if account_ids:
        placeholders = ", ".join("?" for _ in account_ids)
        conn.execute(f"DELETE FROM account_tags WHERE account_id IN ({placeholders})", account_ids)
        conn.execute(f"DELETE FROM account_refresh_logs WHERE account_id IN ({placeholders})", account_ids)
        conn.execute(f"DELETE FROM account_claim_logs WHERE account_id IN ({placeholders})", account_ids)
        conn.execute(f"DELETE FROM account_project_usage WHERE account_id IN ({placeholders})", account_ids)
        conn.execute(f"DELETE FROM accounts WHERE id IN ({placeholders})", account_ids)

    conn.execute("DELETE FROM temp_email_messages WHERE email_address IN (?, ?, ?, ?)", DEMO_TEMP_EMAILS)
    conn.execute("DELETE FROM temp_emails WHERE email IN (?, ?, ?, ?)", DEMO_TEMP_EMAILS)
    conn.execute("DELETE FROM verification_extract_logs WHERE trace_id LIKE 'demo-trace-%'")
    conn.execute("DELETE FROM external_api_consumer_usage_daily WHERE consumer_key IN (?, ?, ?)", DEMO_CONSUMER_KEYS)
    conn.execute("DELETE FROM audit_logs WHERE operator = ? OR trace_id LIKE 'demo-audit-%'", (DEMO_OPERATOR,))
    conn.execute("DELETE FROM refresh_runs WHERE id LIKE 'demo-refresh-%'")


def _ensure_demo_group(conn: sqlite3.Connection) -> int:
    conn.execute(
        """
        INSERT OR IGNORE INTO groups (name, description, color, is_system)
        VALUES (?, ?, ?, 0)
        """,
        (DEMO_GROUP_NAME, "Synthetic local demo data. Safe to delete.", "#2f6fed"),
    )
    row = conn.execute("SELECT id FROM groups WHERE name = ?", (DEMO_GROUP_NAME,)).fetchone()
    return int(row["id"])


def _insert_accounts(conn: sqlite3.Connection, group_id: int, now: datetime) -> list[int]:
    from mailops.security.crypto import encrypt_data

    rows = [
        {
            "email": "graph.orders@demo.local",
            "password": "demo-password-placeholder",
            "client_id": "demo-client-id",
            "refresh_token": "demo-refresh-token-placeholder",
            "account_type": "outlook",
            "provider": "outlook",
            "imap_host": "",
            "imap_port": 993,
            "imap_password": "",
            "remark": "Demo Outlook account with cached verification summary",
            "status": "active",
            "pool_status": "available",
            "latest_email_subject": "Your Acme checkout code is 482913",
            "latest_email_from": "Acme Checkout <no-reply@acme.example>",
            "latest_email_folder": "Inbox",
            "latest_email_received_at": _iso(now - timedelta(minutes=14)),
            "latest_verification_code": "482913",
            "latest_verification_folder": "Inbox",
            "latest_verification_received_at": _iso(now - timedelta(minutes=14)),
            "success_count": 7,
            "fail_count": 1,
        },
        {
            "email": "imap.signup@demo.local",
            "password": "",
            "client_id": "",
            "refresh_token": "",
            "account_type": "imap",
            "provider": "custom_imap",
            "imap_host": "imap.demo.local",
            "imap_port": 993,
            "imap_password": "demo-imap-password-placeholder",
            "remark": "Demo generic IMAP mailbox",
            "status": "active",
            "pool_status": "available",
            "latest_email_subject": "Confirm your developer portal login",
            "latest_email_from": "Portal <login@portal.example>",
            "latest_email_folder": "Inbox",
            "latest_email_received_at": _iso(now - timedelta(minutes=25)),
            "latest_verification_code": "739204",
            "latest_verification_folder": "Inbox",
            "latest_verification_received_at": _iso(now - timedelta(minutes=25)),
            "success_count": 3,
            "fail_count": 0,
        },
        {
            "email": "pool.reserve@demo.local",
            "password": "demo-password-placeholder",
            "client_id": "demo-client-id-reserve",
            "refresh_token": "demo-refresh-token-placeholder",
            "account_type": "outlook",
            "provider": "outlook",
            "imap_host": "",
            "imap_port": 993,
            "imap_password": "",
            "remark": "Demo pool mailbox currently leased to a signup worker",
            "status": "active",
            "pool_status": "claimed",
            "latest_email_subject": "Queue health report",
            "latest_email_from": "Ops <ops@example.test>",
            "latest_email_folder": "Inbox",
            "latest_email_received_at": _iso(now - timedelta(hours=1)),
            "latest_verification_code": "",
            "latest_verification_folder": "",
            "latest_verification_received_at": "",
            "success_count": 9,
            "fail_count": 2,
        },
    ]
    account_ids: list[int] = []
    for index, item in enumerate(rows):
        claimed_at = _iso(now - timedelta(minutes=6)) if item["pool_status"] == "claimed" else None
        lease_expires_at = _iso(now + timedelta(minutes=14)) if item["pool_status"] == "claimed" else None
        conn.execute(
            """
            INSERT INTO accounts (
                email, password, client_id, refresh_token, account_type, provider,
                imap_host, imap_port, imap_password, group_id, remark, status,
                last_refresh_at, created_at, updated_at, telegram_push_enabled,
                latest_email_subject, latest_email_from, latest_email_folder,
                latest_email_received_at, latest_verification_code,
                latest_verification_folder, latest_verification_received_at,
                pool_status, claimed_by, claimed_at, lease_expires_at, claim_token,
                last_claimed_at, last_result, last_result_detail, success_count,
                fail_count, email_domain, claimed_project_key,
                preferred_verification_channel
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            (
                item["email"],
                encrypt_data(item["password"]) if item["password"] else "",
                item["client_id"],
                encrypt_data(item["refresh_token"]) if item["refresh_token"] else "",
                item["account_type"],
                item["provider"],
                item["imap_host"],
                item["imap_port"],
                encrypt_data(item["imap_password"]) if item["imap_password"] else "",
                group_id,
                item["remark"],
                item["status"],
                _sqlite_ts(now - timedelta(minutes=10 + index * 8)),
                _sqlite_ts(now - timedelta(days=3 + index)),
                _sqlite_ts(now - timedelta(minutes=4 + index)),
                item["latest_email_subject"],
                item["latest_email_from"],
                item["latest_email_folder"],
                item["latest_email_received_at"],
                item["latest_verification_code"],
                item["latest_verification_folder"],
                item["latest_verification_received_at"],
                item["pool_status"],
                "signup-worker" if item["pool_status"] == "claimed" else None,
                claimed_at,
                lease_expires_at,
                "demo-claim-token" if item["pool_status"] == "claimed" else None,
                claimed_at,
                "success" if item["pool_status"] != "claimed" else "claimed",
                "Synthetic demo lifecycle row",
                item["success_count"],
                item["fail_count"],
                item["email"].split("@", 1)[1],
                "demo-registration" if item["pool_status"] == "claimed" else None,
                "imap_ssl" if item["account_type"] == "imap" else "graph_delta",
            ),
        )
        account_ids.append(int(conn.execute("SELECT id FROM accounts WHERE email = ?", (item["email"],)).fetchone()["id"]))
    return account_ids


def _insert_temp_mailboxes(conn: sqlite3.Connection, now: datetime) -> list[int]:
    rows = [
        ("duck.demo@temp.demo.local", "duckmail", "DuckMail mail.tm-compatible demo mailbox", "available"),
        ("lol.demo@temp.demo.local", "tempmail_lol", "TempMail.lol demo mailbox", "available"),
        ("nator.demo@mail.example", "emailnator", "Emailnator demo mailbox", "available"),
        ("worker.demo@temp.demo.local", "cloudflare_temp_mail", "Cloudflare Worker demo mailbox", "claimed"),
    ]
    temp_ids: list[int] = []
    for index, (email, source, note, pool_status) in enumerate(rows):
        prefix, domain = email.split("@", 1)
        meta = {
            "demo": True,
            "provider_name": source,
            "note": note,
            "secret_policy": "placeholders-only",
        }
        claimed_at = _iso(now - timedelta(minutes=11)) if pool_status == "claimed" else None
        conn.execute(
            """
            INSERT INTO temp_emails (
                email, status, mailbox_type, visible_in_ui, source, prefix, domain,
                task_token, consumer_key, caller_id, task_id, finished_at, meta_json,
                created_at, updated_at, pool_status, claimed_by, claimed_at,
                lease_expires_at, claim_token, last_claimed_at, last_result
            )
            VALUES (?, 'active', 'user', 1, ?, ?, ?, NULL, NULL, NULL, NULL, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                email,
                source,
                prefix,
                domain,
                json.dumps(meta, sort_keys=True),
                _sqlite_ts(now - timedelta(days=2, hours=index)),
                _sqlite_ts(now - timedelta(minutes=3 + index)),
                pool_status,
                "signup-worker" if pool_status == "claimed" else None,
                claimed_at,
                _iso(now + timedelta(minutes=19)) if pool_status == "claimed" else None,
                "demo-temp-claim" if pool_status == "claimed" else None,
                claimed_at,
                "claimed" if pool_status == "claimed" else "success",
            ),
        )
        temp_ids.append(int(conn.execute("SELECT id FROM temp_emails WHERE email = ?", (email,)).fetchone()["id"]))
    return temp_ids


def _insert_temp_messages(conn: sqlite3.Connection, now: datetime) -> None:
    messages = [
        ("duck.demo@temp.demo.local", "duck-1", "no-reply@acme.example", "DuckMail signup code 391247", "Your verification code is 391247.", 1),
        ("duck.demo@temp.demo.local", "duck-2", "alerts@acme.example", "Welcome to Acme", "Your demo registration mailbox is ready.", 2),
        ("lol.demo@temp.demo.local", "lol-1", "login@saas.example", "Security code 820114", "Use 820114 to finish signing in.", 3),
        ("nator.demo@mail.example", "nator-1", "team@workspace.example", "Confirm email address", "Click the confirmation link in this synthetic message.", 4),
        ("worker.demo@temp.demo.local", "worker-1", "robot@ci.example", "CI worker mailbox code 640288", "Code: 640288", 5),
        ("worker.demo@temp.demo.local", "worker-2", "ops@example.test", "Pool lease notice", "This mailbox is currently claimed by signup-worker.", 6),
    ]
    for email, message_id, sender, subject, content, minutes in messages:
        created = now - timedelta(minutes=minutes * 7)
        conn.execute(
            """
            INSERT INTO temp_email_messages (
                message_id, email_address, from_address, subject, content,
                html_content, has_html, timestamp, raw_content, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                message_id,
                email,
                sender,
                subject,
                content,
                f"<p>{content}</p>",
                1,
                int(created.timestamp()),
                json.dumps({"demo": True, "message_id": message_id}, sort_keys=True),
                _sqlite_ts(created),
            ),
        )


def _insert_pool_and_observability(conn: sqlite3.Connection, account_ids: list[int], temp_ids: list[int], now: datetime) -> None:
    claim_rows = [
        (account_ids[0], "demo-claim-001", "signup-worker", "checkout-flow", "claim", None, "leased graph demo", now - timedelta(hours=3)),
        (account_ids[0], "demo-claim-001", "signup-worker", "checkout-flow", "complete", "success", "code extracted", now - timedelta(hours=2, minutes=52)),
        (account_ids[2], "demo-claim-token", "signup-worker", "registration-flow", "claim", None, "active demo lease", now - timedelta(minutes=6)),
    ]
    for account_id, token, caller_id, task_id, action, result, detail, created in claim_rows:
        conn.execute(
            """
            INSERT INTO account_claim_logs (
                account_id, claim_token, caller_id, task_id, action, result,
                detail, claimed_at, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (account_id, token, caller_id, task_id, action, result, detail, _iso(created), _iso(created)),
        )

    project_rows = [
        (account_ids[0], "demo-webhook", "checkout-flow", now - timedelta(hours=3), now - timedelta(hours=2, minutes=52), 1),
        (account_ids[1], "demo-ci-worker", "registration-flow", now - timedelta(hours=5), now - timedelta(hours=4, minutes=47), 2),
    ]
    for account_id, consumer_key, project_key, first_claimed, last_success, success_count in project_rows:
        conn.execute(
            """
            INSERT INTO account_project_usage (
                account_id, consumer_key, project_key, first_claimed_at,
                last_claimed_at, first_success_at, last_success_at, success_count
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                account_id,
                consumer_key,
                project_key,
                _iso(first_claimed),
                _iso(last_success),
                _iso(last_success),
                _iso(last_success),
                success_count,
            ),
        )

    channels = [
        (account_ids[0], "graph_delta", "code", "482913", 360, 0, None),
        (account_ids[1], "imap_ssl", "code", "739204", 420, 0, None),
        (account_ids[2], "graph_delta", "none", None, 850, 1, "NO_CODE_FOUND"),
        (-temp_ids[0], "temp_mail", "code", "391247", 250, 0, None),
        (-temp_ids[1], "temp_mail", "code", "820114", 280, 0, None),
        (-temp_ids[2], "temp_mail", "link", None, 310, 0, None),
        (-temp_ids[3], "temp_mail", "code", "640288", 260, 0, None),
        (account_ids[0], "ai_fallback", "code", "482913", 1100, 1, None),
    ]
    for index, (account_id, channel, result_type, code, duration_ms, used_ai, error_code) in enumerate(channels):
        started = now - timedelta(minutes=12 + index * 19)
        conn.execute(
            """
            INSERT INTO verification_extract_logs (
                account_id, channel, started_at, finished_at, duration_ms,
                result_type, code_found, used_ai, error_code, trace_id, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                account_id,
                channel,
                started.timestamp(),
                (started + timedelta(milliseconds=duration_ms)).timestamp(),
                duration_ms,
                result_type,
                code,
                used_ai,
                error_code,
                f"demo-trace-{index + 1:02d}",
                started.timestamp(),
            ),
        )

    usage_rows = [
        ("demo-webhook", "Checkout Worker", "checkout", "/api/v1/external/mailbox-sessions/start", 38, 37, 1, "ok", now - timedelta(minutes=9)),
        ("demo-webhook", "Checkout Worker", "checkout", "/api/v1/external/mailbox-sessions/read", 92, 89, 3, "ok", now - timedelta(minutes=6)),
        ("demo-webhook", "Checkout Worker", "checkout", "/api/v1/external/mailbox-sessions/close", 36, 36, 0, "ok", now - timedelta(minutes=5)),
        ("demo-browser-extension", "Browser Extension", "extension", "/api/v1/external/mailboxes", 55, 55, 0, "ok", now - timedelta(minutes=17)),
        ("demo-browser-extension", "Browser Extension", "extension", "/api/v1/external/verification-code", 24, 22, 2, "ok", now - timedelta(minutes=11)),
        ("demo-ci-worker", "CI Worker", "ci", "/api/v1/external/providers", 18, 18, 0, "ok", now - timedelta(minutes=40)),
        ("demo-ci-worker", "CI Worker", "ci", "/api/v1/external/pool/claim-random", 14, 12, 2, "error", now - timedelta(minutes=37)),
        ("demo-ci-worker", "CI Worker", "ci", "/api/v1/external/temp-emails/apply", 11, 11, 0, "ok", now - timedelta(minutes=35)),
        ("demo-ci-worker", "CI Worker", "ci", "/api/v1/external/integration-bundle", 9, 9, 0, "ok", now - timedelta(minutes=32)),
    ]
    usage_date = now.date().isoformat()
    for consumer_key, consumer_name, caller_id, endpoint, total, success, errors, last_status, last_used in usage_rows:
        conn.execute(
            """
            INSERT INTO external_api_consumer_usage_daily (
                consumer_key, consumer_name, caller_id, usage_date, date, endpoint,
                total_count, call_count, success_count, error_count, last_status,
                last_used_at, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            (
                consumer_key,
                consumer_name,
                caller_id,
                usage_date,
                usage_date,
                endpoint,
                total,
                total,
                success,
                errors,
                last_status,
                _iso(last_used),
            ),
        )

    refresh_started = now - timedelta(minutes=18)
    conn.execute(
        """
        INSERT INTO refresh_runs (
            id, trigger_source, status, requested_by_ip, requested_by_user_agent,
            started_at, finished_at, total, success_count, failed_count, message, trace_id
        )
        VALUES (?, 'demo_seed', 'success', '127.0.0.1', 'seed_demo_workspace', ?, ?, 3, 2, 1, ?, ?)
        """,
        (
            "demo-refresh-latest",
            _sqlite_ts(refresh_started),
            _sqlite_ts(refresh_started + timedelta(seconds=23)),
            "Synthetic refresh summary for local demo workspace",
            "demo-audit-refresh",
        ),
    )

    audit_rows = [
        ("demo_seed", "database", "workspace", "ok", "Demo workspace seeded"),
        ("external_api_access", "external_api", "/api/v1/external/mailbox-sessions/start", "ok", "Checkout worker started a mailbox session"),
        ("pool_claim", "account", "pool.reserve@demo.local", "ok", "Mailbox leased to signup worker"),
    ]
    for index, (action, resource_type, resource_id, status, detail) in enumerate(audit_rows):
        conn.execute(
            """
            INSERT INTO audit_logs (
                action, resource_type, resource_id, user_ip, operator,
                status, details, trace_id, created_at
            )
            VALUES (?, ?, ?, '127.0.0.1', ?, ?, ?, ?, ?)
            """,
            (
                action,
                resource_type,
                resource_id,
                DEMO_OPERATOR,
                status,
                json.dumps({"demo": True, "detail": detail}, sort_keys=True),
                f"demo-audit-{index + 1:02d}",
                _sqlite_ts(now - timedelta(minutes=4 + index * 8)),
            ),
        )


def seed_demo_workspace(db_path: Path, *, reset: bool = False) -> dict[str, Any]:
    _set_demo_env(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if reset:
        _remove_sqlite_files(db_path)

    from mailops.db import create_sqlite_connection, init_db

    with redirect_stdout(io.StringIO()):
        init_db(database_path=str(db_path))
    conn = create_sqlite_connection(str(db_path))
    try:
        now = _utc_now()
        _delete_demo_rows(conn)
        group_id = _ensure_demo_group(conn)
        account_ids = _insert_accounts(conn, group_id, now)
        temp_ids = _insert_temp_mailboxes(conn, now)
        _insert_temp_messages(conn, now)
        _insert_pool_and_observability(conn, account_ids, temp_ids, now)
        conn.commit()
        counts = _collect_counts(conn)
    finally:
        conn.close()

    plan = _demo_plan(db_path)
    return {
        "success": True,
        "database_path": str(db_path),
        "reset": bool(reset),
        "login_password": DEMO_LOGIN_PASSWORD,
        "startup_command": plan["startup_command"],
        "counts": counts,
    }


def _collect_counts(conn: sqlite3.Connection) -> dict[str, int]:
    queries = {
        "accounts": ("SELECT COUNT(*) AS c FROM accounts WHERE email IN (?, ?, ?)", DEMO_ACCOUNT_EMAILS),
        "temp_emails": ("SELECT COUNT(*) AS c FROM temp_emails WHERE email IN (?, ?, ?, ?)", DEMO_TEMP_EMAILS),
        "temp_email_messages": ("SELECT COUNT(*) AS c FROM temp_email_messages WHERE email_address IN (?, ?, ?, ?)", DEMO_TEMP_EMAILS),
        "verification_extract_logs": ("SELECT COUNT(*) AS c FROM verification_extract_logs WHERE trace_id LIKE 'demo-trace-%'", ()),
        "external_api_consumer_usage_daily": ("SELECT COUNT(*) AS c FROM external_api_consumer_usage_daily WHERE consumer_key IN (?, ?, ?)", DEMO_CONSUMER_KEYS),
        "account_claim_logs": ("SELECT COUNT(*) AS c FROM account_claim_logs WHERE claim_token LIKE 'demo-claim%'", ()),
        "account_project_usage": ("SELECT COUNT(*) AS c FROM account_project_usage WHERE consumer_key IN (?, ?, ?)", DEMO_CONSUMER_KEYS),
        "audit_logs": ("SELECT COUNT(*) AS c FROM audit_logs WHERE operator = ?", (DEMO_OPERATOR,)),
        "refresh_runs": ("SELECT COUNT(*) AS c FROM refresh_runs WHERE id LIKE 'demo-refresh-%'", ()),
    }
    counts: dict[str, int] = {}
    for key, (sql, params) in queries.items():
        row = conn.execute(sql, params).fetchone()
        counts[key] = int(row["c"] or 0)
    return counts


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Seed a local-only demo workspace database for Outlook Email Plus.")
    parser.add_argument("--database", "--db", dest="database", default="", help="Target SQLite database path. Defaults to output/demo/mailops-demo.db.")
    parser.add_argument("--reset", action="store_true", help="Remove the target SQLite database before seeding it.")
    parser.add_argument("--dry-run", action="store_true", help="Print the planned target and row counts without touching the database.")
    parser.add_argument("--format", choices=("text", "json"), default="text", help="Output format. Default: text.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    db_path = _resolve_db_path(args.database)
    if args.dry_run:
        payload: dict[str, Any] = {"success": True, "dry_run": True, **_demo_plan(db_path)}
    else:
        payload = seed_demo_workspace(db_path, reset=bool(args.reset))

    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    else:
        if payload.get("dry_run"):
            print(f"Demo database target: {payload['database_path']}")
            print("Dry run only; no database was created or changed.")
        else:
            print(f"Demo workspace database seeded: {payload['database_path']}")
            print(f"Login password: {payload['login_password']}")
        print("Start with:")
        print(payload["startup_command"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
