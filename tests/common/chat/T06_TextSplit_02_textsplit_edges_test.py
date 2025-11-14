# -*- coding: utf-8 -*-
"""
M02:T06-02 unittest suite

目的:
- textsplit の未到達分岐を網羅し、境界条件の動作を確認する。

対象:
- common/chat/textsplit.py
"""

import unittest
from tests._report import run_unittest_suite


def _load_targets():
    from common.chat import textsplit as TS  # type: ignore
    return TS, TS.split_text


class TextSplitEdgesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod, cls.split = _load_targets()

    def test_01_min_unit(self):
        # [M02:T06-02-01] max_chars=1 → 1文字ずつ分割
        out = self.split("abcd", max_chars=1, split_sentences=False)
        self.assertEqual(out, ["a", "b", "c", "d"])

    def test_02_period_space_sentence(self):
        # [M02:T06-02-02] ". " での文末分割（先頭空白が残らないこと）
        text = "Hello. World. Test."
        out = self.split(text, max_chars=50, split_sentences=True)
        self.assertEqual(out, ["Hello.", "World.", "Test."])

    def test_03_crlf_newlines(self):
        # [M02:T06-02-03] CRLF 混在
        text = "line1\r\nline2\r\nline3"
        out = self.split(text, max_chars=10, split_sentences=False)
        self.assertTrue(all(len(s) <= 10 for s in out))
        self.assertEqual("".join(out), text)

    def test_04_exact_boundary(self):
        # [M02:T06-02-04] max_chars ジャスト境界
        text = "12345"
        out = self.split(text, max_chars=5, split_sentences=False)
        self.assertEqual(out, ["12345"])

    def test_05_negative_raises(self):
        # [M02:T06-02-05] max_chars < 1 → ValueError
        with self.assertRaises(ValueError):
            self.split("abc", max_chars=0)
        with self.assertRaises(ValueError):
            self.split("abc", max_chars=-10)

    def test_06_non_int_raises(self):
        # [M02:T06-02-06] max_chars が int 以外 → TypeError
        with self.assertRaises(TypeError):
            self.split("abc", max_chars="10")  # type: ignore

    def test_07_super_long_single_token(self):
        # [M02:T06-02-07] 超長単語: 120 文字を 50 ずつハード分割
        text = "X" * 120
        out = self.split(text, max_chars=50, split_sentences=False)
        self.assertEqual(out, ["X" * 50, "X" * 50, "X" * 20])
        self.assertEqual("".join(out), text)


if __name__ == "__main__":
    mapping = {
        "test_01_min_unit": ("M02:T06-02-01", "max_chars=1 の極小分割"),
        "test_02_period_space_sentence": ("M02:T06-02-02", '英文 ". " 文末分割'),
        "test_03_crlf_newlines": ("M02:T06-02-03", "CRLF 混在の改行処理"),
        "test_04_exact_boundary": ("M02:T06-02-04", "max_chars ジャスト境界"),
        "test_05_negative_raises": ("M02:T06-02-05", "負の値/0 → ValueError"),
        "test_06_non_int_raises": ("M02:T06-02-06", "非 int → TypeError"),
        "test_07_super_long_single_token": ("M02:T06-02-07", "超長トークンのハード分割"),
    }
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TextSplitEdgesTest)
    run_unittest_suite("M02:T06-02", suite, mapping)
