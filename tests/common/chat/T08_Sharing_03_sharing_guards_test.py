# -*- coding: utf-8 -*-
"""
T08-03 : Sharing Session Guards / Edge Inputs
対象: common.chat.sharing

目的:
- import_session の入力ガード（None/bytes/空文字/JSONだがdict以外）を網羅
- export_session の入力ガード（None/想定外型）を網羅
- share_to_guild の引数ガード（guild_id/session）を網羅（実装がガードを持つ場合）
"""

import json
import unittest
from typing import Any, Dict

from tests._report import run_unittest_suite


class SharingGuardsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from common.chat import sharing as S  # type: ignore
        cls.mod = S

    def _base_session(self) -> Dict[str, Any]:
        return {
            "id": "s1",
            "ts": 1,
            "provider": "openai",
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": "hi"}],
        }

    # [T08-03-01] import_session: 空文字入力は安全に失敗（{} or None）
    def test_01_import_empty_string(self):
        out = self.mod.import_session("")
        self.assertTrue(out is None or isinstance(out, dict))

    # [T08-03-02] import_session: JSONだが dict ではない（list）→ 安全に失敗（{} or None）
    def test_02_import_json_list(self):
        raw = json.dumps([1, 2, 3])
        out = self.mod.import_session(raw)
        self.assertTrue(out is None or isinstance(out, dict))

    # [T08-03-03] import_session: JSONだが dict ではない（number）→ 安全に失敗（{} or None）
    def test_03_import_json_number(self):
        raw = "123"
        out = self.mod.import_session(raw)
        self.assertTrue(out is None or isinstance(out, dict))

    # [T08-03-04] import_session: bytes 入力（受ける/拒否どちらでも落ちない）
    def test_04_import_bytes(self):
        raw = json.dumps(self._base_session()).encode("utf-8")
        try:
            out = self.mod.import_session(raw)  # type: ignore[arg-type]
        except Exception as e:
            self.fail(f"import_session(bytes) should not raise, but raised: {e}")
        self.assertTrue(out is None or isinstance(out, dict))

    # [T08-03-05] export_session: None/想定外型でも落ちない（str/dictのどちらでもよいが例外は出さない）
    def test_05_export_invalid_input(self):
        try:
            out = self.mod.export_session(None)  # type: ignore[arg-type]
        except Exception as e:
            self.fail(f"export_session(None) should not raise, but raised: {e}")
        # 実装により str/dict/None などがあり得るため型は強制しない
        self.assertTrue(out is None or isinstance(out, (str, dict)))

    # [T08-03-06] share_to_guild: guild_id が不正型でも落ちない（ガードがあれば通る）
    def test_06_share_to_guild_invalid_guild_id(self):
        if not hasattr(self.mod, "share_to_guild"):
            self.skipTest("share_to_guild not found")
        try:
            _ = self.mod.share_to_guild(guild_id="x", session=self._base_session())  # type: ignore[arg-type]
        except Exception as e:
            self.fail(f"share_to_guild(invalid guild_id) should not raise, but raised: {e}")

    # [T08-03-07] share_to_guild: session が不正でも落ちない（ガードがあれば通る）
    def test_07_share_to_guild_invalid_session(self):
        if not hasattr(self.mod, "share_to_guild"):
            self.skipTest("share_to_guild not found")
        try:
            _ = self.mod.share_to_guild(guild_id=1, session="x")  # type: ignore[arg-type]
        except Exception as e:
            self.fail(f"share_to_guild(invalid session) should not raise, but raised: {e}")


if __name__ == "__main__":
    mapping = {
        "test_01_import_empty_string": ("COMMON-CHAT:T08-03-01", "import: 空文字入力の安全ガード"),
        "test_02_import_json_list": ("COMMON-CHAT:T08-03-02", "import: JSON(list) 入力の安全ガード"),
        "test_03_import_json_number": ("COMMON-CHAT:T08-03-03", "import: JSON(number) 入力の安全ガード"),
        "test_04_import_bytes": ("COMMON-CHAT:T08-03-04", "import: bytes 入力の安全ガード"),
        "test_05_export_invalid_input": ("COMMON-CHAT:T08-03-05", "export: None/不正型入力の安全ガード"),
        "test_06_share_to_guild_invalid_guild_id": ("COMMON-CHAT:T08-03-06", "share_to_guild: guild_id 不正型ガード"),
        "test_07_share_to_guild_invalid_session": ("COMMON-CHAT:T08-03-07", "share_to_guild: session 不正型ガード"),
    }
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(SharingGuardsTest)
    run_unittest_suite("COMMON-CHAT:T08-03 common/chat/sharing guards", suite, mapping)
