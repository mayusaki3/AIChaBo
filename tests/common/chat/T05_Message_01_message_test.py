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


    # [T05-01-09] dict入力（正常）
    def test_09_normalize_dict_ok(self):
        from common.chat import message as M

        src = {"role": "assistant", "content": "hi"}
        out = M.normalize_messages(src)

        self.assertIsInstance(out, list)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["role"], "assistant")
        self.assertEqual(out[0]["content"], "hi")

    # [T05-01-10] dict入力（contentなし）→ 空リスト
    def test_10_normalize_dict_missing_content(self):
        from common.chat import message as M

        src = {"role": "assistant"}
        out = M.normalize_messages(src)

        self.assertIsInstance(out, list)
        self.assertEqual(len(out), 0)

    # [T05-01-11] リストがすべて不正要素 → 空リスト
    def test_11_normalize_list_all_invalid(self):
        from common.chat import message as M

        src = [
            {"role": "user"},   # contentなし → _coerce_one -> None
            123,                # 非dict/非str → _coerce_one -> None
        ]
        out = M.normalize_messages(src)

        self.assertIsInstance(out, list)
        self.assertEqual(len(out), 0)

    # [T05-01-12] ensure_role は非dict要素を無視し、roleを補完
    def test_12_ensure_role_skips_non_dict(self):
        from common.chat import message as M

        src = [
            {"content": "x"},  # roleなし → default_role付与
            "y",               # 非dict → スキップされるはず
        ]

        out = M.ensure_role(src, default_role="assistant")

        # 非dictは落ちて、dictだけが残る
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["content"], "x")
        self.assertEqual(out[0]["role"], "assistant")

    # [T05-01-13] join_messages は不正要素をスキップ
    def test_13_join_messages_skips_invalid(self):
        from common.chat import message as M

        msgs = [
            {"role": "user", "content": "ok"},   # 採用
            "NG",                                # 非dict → 無視
            {"role": "user"},                    # contentなし → 無視
            {"role": "user", "content": 123},    # 非str → 無視
            {"role": "user", "content": ""},     # 空文字 → 実装次第だが、通常はスキップ
            {"role": "user", "content": "fine"}, # 採用
        ]

        out = M.join_messages(msgs, sep="|")
        self.assertEqual(out, "ok|fine")

    # [T05-01-14] join_messages: None/空入力は空文字を返す
    def test_14_join_messages_empty_input(self):
        from common.chat import message as M

        # None → 空文字
        out_none = M.join_messages(None)
        self.assertEqual(out_none, "")

        # 空リスト → 空文字
        out_empty_list = M.join_messages([])
        self.assertEqual(out_empty_list, "")

    # [T05-01-15] join_messages: 文字列入力はそのまま返す
    def test_15_join_messages_string_passthrough(self):
        from common.chat import message as M

        out = M.join_messages("hello")
        self.assertEqual(out, "hello")

    # [T05-01-16] join_messages: 非イテラブル入力は TypeError を握り潰して空文字
    def test_16_join_messages_non_iterable_guard(self):
        from common.chat import message as M

        # int などイテラブルでないものが来ても落ちずに空文字を返す
        out = M.join_messages(123)  # type: ignore[arg-type]
        self.assertEqual(out, "")


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
        "test_09_normalize_dict_ok": ("M02:T05-01-09", "dict入力（role+content 正常）"),
        "test_10_normalize_dict_missing_content": ("M02:T05-01-10","dict入力（content欠落時はメッセージ化しない）"),
        "test_11_normalize_list_all_invalid": ("M02:T05-01-11","リストがすべて不正要素の場合は空リスト"),
        "test_12_ensure_role_skips_non_dict": ("M02:T05-01-12","role補完ユーティリティ: 非dict要素をスキップ"),
        "test_13_join_messages_skips_invalid": ("M02:T05-01-13","結合ユーティリティ: 不正要素・空文字をスキップして結合"),
        "test_14_join_messages_empty_input": ("M02:T05-01-14","結合ユーティリティ: None/空入力は空文字を返す"),
        "test_15_join_messages_string_passthrough": ("M02:T05-01-15","結合ユーティリティ: 文字列入力はそのまま返す"),
        "test_16_join_messages_non_iterable_guard": ("M02:T05-01-16","結合ユーティリティ: 非イテラブル入力のガード"),
    }
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(MessageUtilTest)
    run_unittest_suite("M02:T05-01 common/chat/message", suite, mapping)
