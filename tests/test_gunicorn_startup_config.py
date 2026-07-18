import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


class GunicornStartupConfigTests(unittest.TestCase):
    def _run_start_script_with_fake_gunicorn(self, extra_env=None):
        shell = shutil.which("sh")
        if not shell:
            self.skipTest("POSIX sh is required to execute scripts/start-gunicorn.sh")

        script = REPO_ROOT / "scripts/start-gunicorn.sh"
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            args_file = tmp / "gunicorn.args"
            fake_gunicorn = tmp / "gunicorn"
            fake_gunicorn.write_text(
                "#!/bin/sh\n" 'printf \'%s\\n\' "$@" > "$GUNICORN_ARGS_FILE"\n',
                encoding="utf-8",
            )
            fake_gunicorn.chmod(0o755)
            env = os.environ.copy()
            env.update(
                {
                    "PATH": f"{tmp}:{env.get('PATH', '')}",
                    "GUNICORN_ARGS_FILE": str(args_file),
                }
            )
            if extra_env:
                env.update(extra_env)
            result = subprocess.run(
                [shell, str(script)],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            args = args_file.read_text(encoding="utf-8").splitlines() if args_file.exists() else []
            return result, args

    def test_dockerfile_uses_configurable_gunicorn_start_script(self):
        dockerfile = _read("Dockerfile")

        self.assertIn("GUNICORN_WORKERS=1", dockerfile)
        self.assertIn("GUNICORN_THREADS=8", dockerfile)
        self.assertIn("GUNICORN_TIMEOUT=120", dockerfile)
        self.assertIn('CMD ["scripts/start-gunicorn.sh"]', dockerfile)
        self.assertNotIn('CMD ["gunicorn", "-w", "1"', dockerfile)
        self.assertIn("chmod +x /app/scripts/start-gunicorn.sh /app/scripts/healthcheck.py", dockerfile)

    def test_dockerfile_uses_shared_healthcheck_script(self):
        dockerfile = _read("Dockerfile")

        self.assertIn(
            'HEALTHCHECK --interval=30s --timeout=5s --start-period=20s CMD ["python", "scripts/healthcheck.py"]', dockerfile
        )
        self.assertNotIn("urllib.request", dockerfile)
        self.assertNotIn('"-c"', dockerfile)

    def test_compose_exposes_gunicorn_concurrency_knobs(self):
        # Pull-based docker-compose.yml stays minimal; knobs live on the build compose.
        compose = _read("docker-compose.build.yml")

        self.assertIn('GUNICORN_WORKERS: "${GUNICORN_WORKERS:-1}"', compose)
        self.assertIn('GUNICORN_THREADS: "${GUNICORN_THREADS:-8}"', compose)
        self.assertIn('GUNICORN_TIMEOUT: "${GUNICORN_TIMEOUT:-120}"', compose)

    def test_compose_uses_shared_healthcheck_script(self):
        compose = _read("docker-compose.build.yml")

        self.assertIn('test: ["CMD", "python", "scripts/healthcheck.py"]', compose)
        self.assertNotIn("urllib.request", compose)

    def test_compose_exposes_temp_mail_provider_env_knobs(self):
        compose = _read("docker-compose.build.yml")

        expected_lines = [
            'TEMP_MAIL_PROVIDER: "${TEMP_MAIL_PROVIDER:-}"',
            'EXTERNAL_POOL_DEFAULT_PROVIDER: "${EXTERNAL_POOL_DEFAULT_PROVIDER:-}"',
            'ACTIVE_MAILBOX_PROVIDERS: "${ACTIVE_MAILBOX_PROVIDERS:-}"',
            'OUTLOOK_EMAIL_PROVIDER_CONFIG_FILE: "${OUTLOOK_EMAIL_PROVIDER_CONFIG_FILE:-}"',
            'MAILTM_API_BASE: "${MAILTM_API_BASE:-}"',
            'DUCKMAIL_API_BASE: "${DUCKMAIL_API_BASE:-}"',
            'DUCKMAIL_BEARER_TOKEN: "${DUCKMAIL_BEARER_TOKEN:-}"',
            'TEMPMAIL_LOL_API_KEY: "${TEMPMAIL_LOL_API_KEY:-}"',
            'TEMP_MAIL_LOL_API_KEY: "${TEMP_MAIL_LOL_API_KEY:-}"',
            'EMAILNATOR_API_KEY: "${EMAILNATOR_API_KEY:-}"',
            'EMAILNATOR_EMAIL_TYPES: "${EMAILNATOR_EMAIL_TYPES:-}"',
            'CF_WORKER_BASE_URL: "${CF_WORKER_BASE_URL:-}"',
            'CF_WORKER_ADMIN_KEY: "${CF_WORKER_ADMIN_KEY:-}"',
        ]
        for line in expected_lines:
            self.assertIn(line, compose)

    def test_env_example_documents_provider_selection_knobs(self):
        env_example = _read(".env.example")

        expected_lines = [
            "# TEMP_MAIL_PROVIDER=mail_tm",
            "# EXTERNAL_POOL_DEFAULT_PROVIDER=auto",
            "# ACTIVE_MAILBOX_PROVIDERS=duckmail,mail_tm,imap",
            "# OUTLOOK_EMAIL_PROVIDER_CONFIG_FILE=.runtime/providers.json",
            "# MAILTM_API_BASE=https://api.mail.tm",
            "# DUCKMAIL_API_BASE=https://api.duckmail.sbs",
            "# DUCKMAIL_BEARER_TOKEN=",
            "# TEMPMAIL_LOL_API_KEY=",
            "# TEMP_MAIL_LOL_API_KEY=",
            "# EMAILNATOR_API_KEY=",
            '# EMAILNATOR_EMAIL_TYPES=["public_gmail_plus"]',
        ]
        for line in expected_lines:
            self.assertIn(line, env_example)

    def test_start_script_keeps_single_worker_default_with_threads(self):
        script = _read("scripts/start-gunicorn.sh")

        self.assertIn(': "${GUNICORN_WORKERS:=1}"', script)
        self.assertIn(': "${GUNICORN_THREADS:=8}"', script)
        self.assertIn(': "${GUNICORN_TIMEOUT:=120}"', script)
        self.assertIn("--threads", script)
        self.assertIn("web_mailops_app:app", script)
        self.assertNotIn("--preload", script)
        self.assertIn("wait-message", script)

    def test_start_script_passes_default_threaded_gunicorn_args(self):
        result, args = self._run_start_script_with_fake_gunicorn()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            args,
            [
                "-w",
                "1",
                "--threads",
                "8",
                "-b",
                "0.0.0.0:5000",
                "--timeout",
                "120",
                "--access-logfile",
                "-",
                "web_mailops_app:app",
            ],
        )

    def test_start_script_allows_env_overrides(self):
        result, args = self._run_start_script_with_fake_gunicorn(
            {
                "GUNICORN_WORKERS": "2",
                "GUNICORN_THREADS": "12",
                "GUNICORN_TIMEOUT": "90",
                "GUNICORN_BIND": "127.0.0.1:5050",
                "GUNICORN_ACCESS_LOGFILE": "/tmp/access.log",
            }
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            args,
            [
                "-w",
                "2",
                "--threads",
                "12",
                "-b",
                "127.0.0.1:5050",
                "--timeout",
                "90",
                "--access-logfile",
                "/tmp/access.log",
                "web_mailops_app:app",
            ],
        )

    def test_start_script_rejects_zero_or_non_numeric_values(self):
        script = REPO_ROOT / "scripts/start-gunicorn.sh"
        self.assertTrue(script.exists())
        self.assertTrue(_read("scripts/start-gunicorn.sh").startswith("#!/bin/sh"))

        result, _args = self._run_start_script_with_fake_gunicorn({"GUNICORN_THREADS": "0"})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("GUNICORN_THREADS must be a positive integer", result.stderr)

        result, _args = self._run_start_script_with_fake_gunicorn({"GUNICORN_WORKERS": "many"})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("GUNICORN_WORKERS must be a positive integer", result.stderr)


if __name__ == "__main__":
    unittest.main()
