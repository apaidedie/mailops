from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from scripts import project_readiness_check
from scripts import seed_demo_workspace


class SeedDemoWorkspaceTests(unittest.TestCase):
    def test_dry_run_json_does_not_create_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "demo.db"
            buffer = StringIO()
            with redirect_stdout(buffer):
                exit_code = seed_demo_workspace.main(["--dry-run", "--database", str(db_path), "--format", "json"])

            payload = json.loads(buffer.getvalue())

        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertTrue(payload["dry_run"])
        self.assertEqual(payload["database_path"], str(db_path))
        self.assertFalse(db_path.exists())

    def test_seed_reset_creates_expected_demo_inventory(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "demo.db"
            result = seed_demo_workspace.seed_demo_workspace(db_path, reset=True)

            self.assertTrue(result["success"])
            self.assertEqual(result["counts"]["accounts"], 3)
            self.assertEqual(result["counts"]["temp_emails"], 4)
            self.assertEqual(result["counts"]["temp_email_messages"], 6)
            self.assertEqual(result["counts"]["verification_extract_logs"], 8)
            self.assertEqual(result["counts"]["external_api_consumer_usage_daily"], 9)
            self.assertIn("web_outlook_app.py", result["startup_command"])

            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            try:
                account_row = conn.execute(
                    "SELECT COUNT(*) AS c FROM accounts WHERE account_type = 'outlook' AND email LIKE '%@demo.local'"
                ).fetchone()
                imap_row = conn.execute(
                    "SELECT COUNT(*) AS c FROM accounts WHERE account_type = 'imap' AND email LIKE '%@demo.local'"
                ).fetchone()
                provider_rows = conn.execute(
                    "SELECT DISTINCT source FROM temp_emails WHERE email IN (?, ?, ?, ?) ORDER BY source",
                    seed_demo_workspace.DEMO_TEMP_EMAILS,
                ).fetchall()
            finally:
                conn.close()

        self.assertGreaterEqual(int(account_row["c"]), 1)
        self.assertGreaterEqual(int(imap_row["c"]), 1)
        self.assertEqual(
            [row["source"] for row in provider_rows],
            ["cloudflare_temp_mail", "duckmail", "emailnator", "tempmail_lol"],
        )

    def test_seed_is_deterministic_on_repeated_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "demo.db"
            first = seed_demo_workspace.seed_demo_workspace(db_path, reset=True)
            second = seed_demo_workspace.seed_demo_workspace(db_path, reset=False)

        self.assertEqual(first["counts"], second["counts"])

    def test_json_output_is_clean_and_secret_scanner_safe(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "demo.db"
            buffer = StringIO()
            with redirect_stdout(buffer):
                exit_code = seed_demo_workspace.main(["--reset", "--database", str(db_path), "--format", "json"])

            stdout = buffer.getvalue()
            payload = json.loads(stdout)
            hits = []
            for name, pattern in project_readiness_check.SECRET_PATTERNS:
                if pattern.search(stdout):
                    hits.append(name)

        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
