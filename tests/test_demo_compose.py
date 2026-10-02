"""tests/test_demo_compose.py — 一键演示栈（docker-compose.demo.yml）契约测试。

无需 Docker 守护进程：以文本契约校验编排结构，覆盖三条安全边界——
1. 演示种子是一次性容器且显式 --reset（遵循「启动流程不自动播种」规范）；
2. 应用等待种子完成后才启动，且只指向演示库；
3. 演示库与生产库文件名隔离，演示站点禁改登录密码。
"""

from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEMO_COMPOSE = REPO_ROOT / "docker-compose.demo.yml"
PROD_COMPOSE = REPO_ROOT / "docker-compose.yml"

DEMO_DB = "data/mailops-demo.db"


def _service_block(text: str, service: str) -> str:
    """提取顶层服务块（以两个空格缩进的 `name:` 为界，到下一个同级键为止）。"""
    lines = text.splitlines()
    starts = [i for i, ln in enumerate(lines) if ln.startswith("  ") and ln.endswith(":") and not ln.startswith("   ")]
    for idx, start in enumerate(starts):
        if lines[start] == f"  {service}:":
            end = starts[idx + 1] if idx + 1 < len(starts) else len(lines)
            return "\n".join(lines[start:end])
    raise AssertionError(f"service block not found: {service}")


class DemoComposeContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.demo_text = DEMO_COMPOSE.read_text(encoding="utf-8")
        cls.prod_text = PROD_COMPOSE.read_text(encoding="utf-8")

    def test_file_declares_both_services(self):
        self.assertIn("  demo-seed:", self.demo_text)
        self.assertIn("  mailops:", self.demo_text)

    def test_seed_is_one_shot_and_explicitly_resets(self):
        seed = _service_block(self.demo_text, "demo-seed")
        self.assertIn('restart: "no"', seed)
        self.assertIn("--reset", seed)
        self.assertIn("scripts/seed_demo_workspace.py", seed)
        self.assertIn(DEMO_DB, seed)

    def test_app_waits_for_seed_and_targets_demo_db(self):
        app = _service_block(self.demo_text, "mailops")
        self.assertIn("condition: service_completed_successfully", app)
        self.assertIn(f'DATABASE_PATH: "{DEMO_DB}"', app)

    def test_demo_login_password_is_locked(self):
        app = _service_block(self.demo_text, "mailops")
        self.assertIn('ALLOW_LOGIN_PASSWORD_CHANGE: "false"', app)

    def test_demo_db_never_collides_with_production_default(self):
        # 生产编排未显式设置 DATABASE_PATH，走应用默认 data/outlook_accounts.db；
        # 两个文件名必须始终错开，演示与生产可共用 ./data 卷。
        self.assertNotIn(DEMO_DB, self.prod_text, "生产编排不得引用演示库文件")
        import os
        from unittest.mock import patch

        from mailops import config

        # 全量套件会把 DATABASE_PATH 指到临时目录；本断言只关心出厂默认值。
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("DATABASE_PATH", None)
            self.assertEqual(config.get_database_path(), "data/outlook_accounts.db")
            self.assertNotEqual(DEMO_DB, config.get_database_path())

    def test_demo_secret_is_the_public_seed_constant(self):
        # 演示密钥与 scripts/seed_demo_workspace.py 的公开常量一致，属演示专用；
        # 生产 compose 不得出现该值。
        seed_script = (REPO_ROOT / "scripts" / "seed_demo_workspace.py").read_text(encoding="utf-8")
        demo_secret = "demo-local-secret-key-32bytes-minimum-0000000000000000"
        self.assertIn(demo_secret, self.demo_text)
        self.assertIn(demo_secret, seed_script)
        self.assertNotIn(demo_secret, self.prod_text)

    def test_dockerfile_pip_index_is_parameterized(self):
        # 默认官方 PyPI（全球可构建），CI 发布流程通过 build-arg 保留清华镜像。
        dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn("ARG PIP_INDEX_URL=https://pypi.org/simple", dockerfile)
        self.assertNotIn("pypi.tuna.tsinghua.edu.cn", dockerfile)
        workflow = (REPO_ROOT / ".github/workflows/docker-build-push.yml").read_text(encoding="utf-8")
        self.assertIn("PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple", workflow)


if __name__ == "__main__":
    unittest.main()
