from __future__ import annotations

import importlib
import io
import os
import runpy
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class WebOutlookAppEntrypointTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory(prefix="outlook-main-entrypoint-")
        self._db_path = Path(self._temp_dir.name) / "test.db"
        self._original_env = {
            key: os.environ.get(key)
            for key in (
                "SECRET_KEY",
                "LOGIN_PASSWORD",
                "SCHEDULER_AUTOSTART",
                "FLASK_ENV",
                "HOST",
                "PORT",
                "DATABASE_PATH",
            )
        }
        if "outlook_web.app" in sys.modules:
            sys.modules["outlook_web.app"]._APP_INSTANCE = None
        sys.modules.pop("web_outlook_app", None)
        os.environ["SECRET_KEY"] = "test-secret-key-32bytes-minimum-0000000000000000"
        os.environ["LOGIN_PASSWORD"] = "testpass123"
        os.environ["SCHEDULER_AUTOSTART"] = "false"
        os.environ["FLASK_ENV"] = "production"
        os.environ["HOST"] = "127.0.0.1"
        os.environ["PORT"] = "5099"
        os.environ["DATABASE_PATH"] = str(self._db_path)
        self.module = importlib.import_module("web_outlook_app")

    def tearDown(self) -> None:
        if "outlook_web.app" in sys.modules:
            sys.modules["outlook_web.app"]._APP_INSTANCE = None
        sys.modules.pop("web_outlook_app", None)
        for key, value in self._original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self._temp_dir.cleanup()

    def test_main_respects_scheduler_autostart_false(self) -> None:
        with (
            patch.object(self.module.scheduler_service, "should_autostart_scheduler", return_value=False) as should_autostart,
            patch.object(self.module.scheduler_service, "init_scheduler") as init_scheduler,
            patch.object(self.module.app, "run") as run_app,
        ):
            self.module.main()

        should_autostart.assert_called_once_with()
        init_scheduler.assert_not_called()
        run_app.assert_called_once_with(debug=False, host="127.0.0.1", port=5099)

    def test_cli_entrypoint_includes_provider_scaffold_command(self) -> None:
        source = Path("web_outlook_app.py").read_text(encoding="utf-8")

        self.assertIn("_TEMP_MAIL_PROVIDER_CLI_COMMANDS", source)
        self.assertIn('"scaffold-provider"', source)
        self.assertIn('"validate-provider"', source)
        self.assertIn("temp_mail_plugin_cli_main(sys.argv[1:])", source)
        self.assertLess(source.index("_TEMP_MAIL_PROVIDER_CLI_COMMANDS"), source.index("app = create_app"))

    def test_entrypoint_configures_utf8_safe_output_before_startup_prints(self) -> None:
        source = Path("web_outlook_app.py").read_text(encoding="utf-8")

        self.assertIn("from outlook_web.runtime_output import configure_process_output", source)
        self.assertIn("configure_process_output()", source)
        self.assertLess(source.index("configure_process_output()"), source.index("from outlook_web.app import create_app"))


class StartScriptSecretOutputTests(unittest.TestCase):
    def test_start_script_does_not_print_generated_secret_key(self) -> None:
        with tempfile.TemporaryDirectory(prefix="outlook-start-secret-") as temp_dir:
            temp_path = Path(temp_dir)
            (temp_path / ".env.example").write_text(
                "SECRET_KEY=your-secret-key-here\nLOGIN_PASSWORD=testpass123\n",
                encoding="utf-8",
            )

            output = io.StringIO()
            with (
                patch("os.getcwd", return_value=str(temp_path)),
                patch("os.path.exists", side_effect=lambda path: (temp_path / path).exists()),
                patch(
                    "shutil.copy",
                    side_effect=lambda source, dest: (temp_path / dest).write_text(
                        (temp_path / source).read_text(encoding="utf-8"), encoding="utf-8"
                    ),
                ),
                patch(
                    "builtins.open",
                    side_effect=lambda file, mode="r", *args, **kwargs: (temp_path / file).open(mode, *args, **kwargs),
                ),
                patch("secrets.token_hex", return_value="fixed-generated-secret"),
                patch("sys.stdout", output),
            ):
                start_script = Path(__file__).resolve().parents[1] / "start.py"
                module_globals = runpy.run_path(str(start_script), run_name="start_test")
                module_globals["ensure_env_file"]()

            printed = output.getvalue()
            self.assertIn("SECRET_KEY 已写入 .env", printed)
            self.assertNotIn("fixed-generated-secret", printed)
            self.assertIn("SECRET_KEY=fixed-generated-secret", (temp_path / ".env").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
