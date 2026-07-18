import ast
import unittest
from pathlib import Path


class ModuleBoundaryTests(unittest.TestCase):
    @staticmethod
    def _collect_import_modules(path: Path) -> set[str]:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        modules: set[str] = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    modules.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    modules.add(node.module)
        return modules

    def _assert_forbidden_imports(self, *, path: Path, forbidden_prefixes: tuple[str, ...]):
        imports = self._collect_import_modules(path)
        for module in sorted(imports):
            for prefix in forbidden_prefixes:
                if module == prefix or module.startswith(prefix + "."):
                    self.fail(f"模块边界违规：{path} 导入了禁止依赖 {module!r}（匹配前缀 {prefix!r}）")

    def test_routes_do_not_import_services_repos_or_legacy(self):
        repo_root = Path(__file__).resolve().parents[1]
        routes_dir = repo_root / "mailops" / "routes"
        self.assertTrue(routes_dir.exists())

        forbidden = (
            "mailops.legacy",
            "mailops.services",
            "mailops.repositories",
            "mailops.db",
        )
        for path in sorted(routes_dir.glob("*.py")):
            if path.name == "__init__.py":
                continue
            self._assert_forbidden_imports(path=path, forbidden_prefixes=forbidden)

    def test_repositories_do_not_depend_on_flask_routes_or_services(self):
        repo_root = Path(__file__).resolve().parents[1]
        repos_dir = repo_root / "mailops" / "repositories"
        self.assertTrue(repos_dir.exists())

        forbidden = (
            "flask",
            "mailops.routes",
            "mailops.services",
            "mailops.legacy",
        )
        for path in sorted(repos_dir.glob("*.py")):
            if path.name == "__init__.py":
                continue
            self._assert_forbidden_imports(path=path, forbidden_prefixes=forbidden)

    def test_services_do_not_depend_on_flask_routes_or_legacy(self):
        repo_root = Path(__file__).resolve().parents[1]
        services_dir = repo_root / "mailops" / "services"
        self.assertTrue(services_dir.exists())

        forbidden = (
            "flask",
            "mailops.routes",
            "mailops.legacy",
        )
        for path in sorted(services_dir.glob("*.py")):
            if path.name == "__init__.py":
                continue
            self._assert_forbidden_imports(path=path, forbidden_prefixes=forbidden)
