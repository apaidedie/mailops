"""tests/test_i18n_coverage.py — 前端 i18n 覆盖率回归门禁。

复用 scripts/i18n_coverage_audit.py 的审计逻辑：
- JS 中 translate*() 显式调用的中文串必须在 i18n.js exactMap 中；
- 模板可见中文文本节点必须被 exactMap 覆盖（豁免清单见 ALLOWED_MISSING）。

新增 UI 文案时若本测试失败，请同步在 static/js/i18n.js 补充英文映射，
或在审计脚本的 ALLOWED_MISSING 里登记豁免原因。
"""

from __future__ import annotations

import unittest

from scripts.i18n_coverage_audit import audit


class I18nCoverageGateTests(unittest.TestCase):
    def test_no_missing_frontend_translations(self):
        self.assertEqual(audit(), 0, "存在未翻译的前端中文串：见上方审计输出")


if __name__ == "__main__":
    unittest.main()
