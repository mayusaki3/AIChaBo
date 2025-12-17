# -*- coding: utf-8 -*-
"""
T08-04 : Sharing Session (Branch Coverage)
対象: common.chat.sharing

目的:
- sharing.py の分岐網羅率（branch coverage）を上げるためのテスト。
- 仕様テスト（T08-01〜03）では踏みにくいフォールバック経路を安全に通す。
"""

import unittest
from typing import Dict, Tuple

from tests._report import run_unittest_suite


class SharingBranchCoverageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from common.chat import sharing as S  # type: ignore
        cls.mod = S

    # [T08-04-01] export: 空dictでも例外にならず str を返す
    def test_01_export_empty_dict(self):
        out = self.mod.export_session({})  # type: ignore[attr-defined]
        self.assertIsInstance(out, str)

    # [T08-04-02] export: 非dict入力でも例外にならず str を返す
    def test_02_export_non_dict(self):
        out1 = self.mod.export_session([])      # type: ignore[arg-type,attr-defined]
        out2 = self.mod.export_session("x")     # type: ignore[arg-type,attr-defined]
        self.assertIsInstance(out1, str)
        self.assertIsInstance(out2, str)

    # [T08-04-03] import: unknown version を含む入力でも dict として復元される
    def test_03_import_unknown_version(self):
        raw = {
            "version": 999,
            "messages": [{"role": "user", "content": "hi"}],
            "provider": "openai",
            "model": "gpt-4o",
        }
        out = self.mod.import_session(raw)  # type: ignore[arg-type,attr-defined]
        self.assertIsInstance(out, dict)
        self.assertIn("messages", out)

    # [T08-04-04] import: messages が list 以外でも安全に list へ補正される
    def test_04_import_messages_not_list(self):
        raw = {
            "version": 1,
            "messages": "invalid",
            "provider": "openai",
            "model": "gpt-4o",
        }
        out = self.mod.import_session(raw)  # type: ignore[arg-type,attr-defined]
        self.assertIsInstance(out, dict)
        self.assertIsInstance(out.get("messages"), list)

    # [T08-04-05] import: legacy 形式で messages 欠落でも messages を補完する
    def test_05_legacy_messages_missing(self):
        raw = {
            "id": "legacy",
            "provider": "openai",
            "model": "gpt-4o",
        }
        out = self.mod.import_session(raw)  # type: ignore[arg-type,attr-defined]
        self.assertIsInstance(out, dict)
        self.assertIn("messages", out)
        self.assertIsInstance(out["messages"], list)

    # [T08-04-06] share_to_guild: no-op 経路（内部保存が未実装でも例外なし）
    def test_06_share_to_guild_noop(self):
        self.mod.share_to_guild(guild_id=1, session={"id": "s1"})  # type: ignore[attr-defined]


if __name__ == "__main__":
    mapping: Dict[str, Tuple[str, str]] = {
        "test_01_export_empty_dict": (
            "COMMON-CHAT:T08-04-01",
            "export_session: 空dict入力でも例外にならず str を返す",
        ),
        "test_02_export_non_dict": (
            "COMMON-CHAT:T08-04-02",
            "export_session: 非dict入力でも例外にならず str を返す",
        ),
        "test_03_import_unknown_version": (
            "COMMON-CHAT:T08-04-03",
            "import_session: unknown version 入力でも dict として復元される",
        ),
        "test_04_import_messages_not_list": (
            "COMMON-CHAT:T08-04-04",
            "import_session: messages が list 以外でも安全に list 補正される",
        ),
        "test_05_legacy_messages_missing": (
            "COMMON-CHAT:T08-04-05",
            "import_session: legacy 形式で messages 欠落でも messages を補完する",
        ),
        "test_06_share_to_guild_noop": (
            "COMMON-CHAT:T08-04-06",
            "share_to_guild: no-op 経路（内部保存未実装でも例外なし）",
        ),
    }

    suite = unittest.defaultTestLoader.loadTestsFromTestCase(SharingBranchCoverageTest)
    run_unittest_suite("COMMON-CHAT:T08-04 common/chat/sharing branch", suite, mapping)
