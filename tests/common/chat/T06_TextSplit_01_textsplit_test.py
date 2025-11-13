# -*- coding: utf-8 -*-
"""
T06-01 : TextSplit Utility
対象: common.chat.textsplit
- 長文分割 / 文区切り / 多言語 / パラメータ検証
"""

import unittest
from tests._report import run_unittest_suite

def _load_targets():
    from common.chat import textsplit as TS  # type: ignore
    split = getattr(TS, "split_text", None) or getattr(TS, "split", None)
    return TS, split


class TextSplitTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod, cls.split = _load_targets()

    def _need(self):
        if not self.split:
            self.skipTest("split_text not found")

    # [T06-01-01] 基本分割
    def test_01_basic(self):
        self._need()
        text = "a" * 120
        out = self.split(text, max_len=50)
        self.assertTrue(all(1 <= len(x) <= 50 for x in out))

    # [T06-01-02] 文単位（和文）
    def test_02_sentences_ja(self):
        self._need()
        text = "一文です。二文目です！三文？"
        out = self.split(text, max_len=50, split_sentences=True)
        self.assertGreaterEqual(len(out), 3)

    # [T06-01-03] 文単位（英文）
    def test_03_sentences_en(self):
        self._need()
        text = "One. Two? Three!"
        out = self.split(text, max_len=50, split_sentences=True)
        self.assertGreaterEqual(len(out), 3)

    # [T06-01-04] 改行混在
    def test_04_newlines(self):
        self._need()
        text = "a\n\nb\nc"
        out = self.split(text, max_len=2, split_sentences=False)
        self.assertTrue(len(out) >= 2)

    # [T06-01-05] 超長単語
    def test_05_super_long_token(self):
        self._need()
        text = "x" * 200
        out = self.split(text, max_len=30)
        self.assertTrue(all(len(x) <= 30 for x in out))

    # [T06-01-06] 空文字
    def test_06_empty(self):
        self._need()
        out = self.split("", max_len=10)
        self.assertIsInstance(out, list)

    # [T06-01-07] 無効パラメータ
    def test_07_invalid_param(self):
        self._need()
        with self.assertRaises(Exception):
            self.split("abc", max_len=0)

    # [T06-01-08] 末尾境界
    def test_08_tail_boundary(self):
        self._need()
        out = self.split("終端。", max_len=10, split_sentences=True)
        self.assertGreaterEqual(len(out), 1)


if __name__ == "__main__":
    mapping = {
        "test_01_basic": ("M02:T06-01-01", "基本分割"),
        "test_02_sentences_ja": ("M02:T06-01-02", "文単位分割（和文）"),
        "test_03_sentences_en": ("M02:T06-01-03", "文単位分割（英文）"),
        "test_04_newlines": ("M02:T06-01-04", "改行混在"),
        "test_05_super_long_token": ("M02:T06-01-05", "超長単語"),
        "test_06_empty": ("M02:T06-01-06", "空文字"),
        "test_07_invalid_param": ("M02:T06-01-07", "無効パラメータ"),
        "test_08_tail_boundary": ("M02:T06-01-08", "末尾境界"),
    }
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TextSplitTest)
    run_unittest_suite("M02:T06-01", suite, mapping)
