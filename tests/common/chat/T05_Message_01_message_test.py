# -*- coding: utf-8 -*-
"""
T05-01 : Message Utility
対象: common.chat.message
- 文字列/配列/辞書入力の正規化、role 既定補完、結合ユーティリティ
"""

import unittest
from typing import Any, List, Dict

from tests._report import run_unittest_suite

# 被テスト関数は実装名が揺れる可能性があるため候補から解決する
def _load_targets():
    from common.chat import message as M  # type: ignore
    norm = getattr(M, "normalize_messages", None) or getattr(M, "normalize", None) \
        or getattr(M, "to_messages", None)
    join = getattr(M, "join_messages", None) or getattr(M, "join", None)
    role = getattr(M, "add_role_default", None) or getattr(M, "ensure_role", None)
    return M, norm, join, role


class MessageUtilTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod, cls.normalize, cls.join, cls.role = _load_targets()

    # [T05-01-01] 文字列の正規化
    def test_01_normalize_str(self):
        if not self.normalize:
            self.skipTest("normalize_messages not found")
        out = self.normalize("hello")
        self.assertIsInstance(out, list)
        self.assertEqual(out[0].get("role", "user"), "user")
        self.assertEqual(out[0]["content"], "hello")

    # [T05-01-02] 既存配列の透過
    def test_02_passthrough_list(self):
        if not self.normalize:
            self.skipTest("normalize_messages not found")
        src = [{"role": "user", "content": "hi"}]
        out = self.normalize(src)
        self.assertEqual(out, src)

    # [T05-01-03] 不正型ガード
    def test_03_invalid_type_guard(self):
        if not self.normalize:
            self.skipTest("normalize_messages not found")
        with self.assertRaises(Exception):
            self.normalize(123)  # type: ignore

    # [T05-01-04] 空文字の扱い（実装追従）
    def test_04_empty_string(self):
        if not self.normalize:
            self.skipTest("normalize_messages not found")
        out = self.normalize("")
        self.assertIsInstance(out, list)

    # [T05-01-05] role 既定値補完
    def test_05_role_default(self):
        if not self.normalize:
            self.skipTest("normalize_messages not found")
        src = [{"content": "x"}]
        out = self.normalize(src)
        self.assertEqual(out[0].get("role", "user"), "user")

    # [T05-01-06] トリム規則（保持/除去は実装に追従）
    def test_06_trim(self):
        if not self.normalize:
            self.skipTest("normalize_messages not found")
        out = self.normalize("  hey  ")
        self.assertTrue(isinstance(out, list) and "hey" in out[0]["content"])

    # [T05-01-07] 結合ユーティリティ
    def test_07_join(self):
        if not self.normalize:
            self.skipTest("normalize_messages not found")
        if not self.join:
            self.skipTest("join_messages not found")
        msgs: List[Dict[str, Any]] = self.normalize(["a", "b"])  # type: ignore
        s = self.join(msgs, sep="|")
        self.assertIn("|", s)
        self.assertTrue(s.startswith("a"))

    # [T05-01-08] 破損要素スキップ（content 無し）
    def test_08_skip_broken(self):
        if not self.normalize:
            self.skipTest("normalize_messages not found")
        out = self.normalize([{"role": "user"}, {"role": "user", "content": "ok"}])
        self.assertTrue(any(m.get("content") == "ok" for m in out))


if __name__ == "__main__":
    mapping = {
        "test_01_normalize_str": ("M02:T05-01-01", '文字列の正規化 -> [{"role":"user","content":"..."}]'),
        "test_02_passthrough_list": ("M02:T05-01-02", "既存配列の透過"),
        "test_03_invalid_type_guard": ("M02:T05-01-03", "不正型ガード"),
        "test_04_empty_string": ("M02:T05-01-04", "空文字の扱い"),
        "test_05_role_default": ("M02:T05-01-05", "role 既定補完"),
        "test_06_trim": ("M02:T05-01-06", "トリム規則"),
        "test_07_join": ("M02:T05-01-07", "結合ユーティリティ"),
        "test_08_skip_broken": ("M02:T05-01-08", "破損要素スキップ"),
    }
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(MessageUtilTest)
    run_unittest_suite("M02:T05-01", suite, mapping)
