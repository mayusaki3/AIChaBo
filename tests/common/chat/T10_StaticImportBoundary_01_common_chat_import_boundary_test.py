# -*- coding: utf-8 -*-
"""
COMMON-CHAT:T10-01 common/chat import boundary 静的検査
目的:
  - common/chat 配下が ai.* を直接 import していないことを検証する。
  - Provider Adapter Registry 導入後の責務境界が維持されていることを確認する。
実行例:
  python -m tests.common.chat.T10_StaticImportBoundary_01_common_chat_import_boundary_test
出力:
  ✅/❌ と [COMMON-CHAT:T10-01-xx] を先頭に持つ行 + SUMMARY（共通レポータ）
"""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

from tests._report import run_unittest_suite


ROOT_DIR = Path(__file__).resolve().parents[3]
COMMON_CHAT_DIR = ROOT_DIR / "common" / "chat"


class StaticImportBoundaryTest(unittest.TestCase):
    """common/chat の AI 層直接依存を静的検査する。"""

    def _iter_python_files(self):
        """common/chat 配下の Python ファイルを列挙する。"""
        for path in COMMON_CHAT_DIR.rglob("*.py"):
            if path.name.startswith("__"):
                continue
            yield path

    def _collect_ai_imports(self):
        """
        ai.* を直接 import している import 文を収集する。

        戻り値:
          [(relative_path, lineno, import_text), ...]
        """
        violations = []

        for path in self._iter_python_files():
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(path))

            for node in ast.walk(tree):
                # import ai.xxx
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name == "ai" or alias.name.startswith("ai."):
                            violations.append(
                                (
                                    str(path.relative_to(ROOT_DIR)),
                                    node.lineno,
                                    f"import {alias.name}",
                                )
                            )

                # from ai.xxx import yyy
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    if module == "ai" or module.startswith("ai."):
                        imported = ", ".join(alias.name for alias in node.names)
                        violations.append(
                            (
                                str(path.relative_to(ROOT_DIR)),
                                node.lineno,
                                f"from {module} import {imported}",
                            )
                        )

        return violations

    # [COMMON-CHAT:T10-01-01] common/chat import boundary:
    #   common/chat 配下が ai.* を直接 import していないこと。
    def test_01_common_chat_has_no_direct_ai_imports(self):
        violations = self._collect_ai_imports()

        if violations:
            details = "\n".join(
                f"{path}:{lineno}: {statement}"
                for path, lineno, statement in violations
            )
            self.fail(
                "common/chat must not directly import ai.* modules:\n"
                f"{details}"
            )


if __name__ == "__main__":
    mapping = {
        "test_01_common_chat_has_no_direct_ai_imports": (
            "COMMON-CHAT:T10-01-01",
            "common chat has no direct ai imports",
        ),
    }

    suite = unittest.defaultTestLoader.loadTestsFromTestCase(
        StaticImportBoundaryTest
    )

    run_unittest_suite(
        "COMMON-CHAT:T10-01 common/chat static import boundary",
        suite,
        mapping,
    )
