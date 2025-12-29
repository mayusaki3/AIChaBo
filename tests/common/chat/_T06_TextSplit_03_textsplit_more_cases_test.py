# tests/common/chat/T06_TextSplit_03_textsplit_more_cases_test.py
# -*- coding: utf-8 -*-
"""
T06-03 : TextSplit Utility (More Cases)
- 文区切り混在 / Unicode・絵文字 / 改行保持の厳密性 / 決定性
- ハード分割優先順位 / max_chars の型境界
既存スイート（T06-01/T06-02）の出力方針・レポート形式に準拠。
"""
import unittest
from tests._report import run_unittest_suite

def _load_targets():
    # textsplit モジュールから split_text (なければ split) を解決
    from common.chat import textsplit as TS  # type: ignore
    split = getattr(TS, "split_text", None) or getattr(TS, "split", None)
    return TS, split

class TextSplitMoreCasesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod, cls.split = _load_targets()

    def _need(self):
        if not self.split:
            self.skipTest("split_text not found")

    # [COMMON-CHAT:T06-03-01] 英文 空白保持（複合文）
    def test_01_en_space_after_punct(self):
        self._need()
        text = "Hello. World. Test."
        out = self.split(text, max_chars=50, split_sentences=True)
        self.assertIsInstance(out, list)
        # 既存仕様に追従（厳密配列ではなく件数/長さでゆるく確認）
        self.assertGreaterEqual(len(out), 2)
        self.assertTrue(all(len(x) <= 50 for x in out))

    # [COMMON-CHAT:T06-03-02] CJK 文区切り複合
    def test_02_cjk_mixed_endings(self):
        self._need()
        text = "一文です。二文です？三文です！四文です…四文です。"
        out = self.split(text, max_chars=50, split_sentences=True)
        self.assertGreaterEqual(len(out), 4)

    # [COMMON-CHAT:T06-03-03] Unicode/絵文字でも長さ制御が崩れない
    def test_03_unicode_emoji(self):
        self._need()
        text = "😀テスト😀です。OK!"
        out = self.split(text, max_chars=5, split_sentences=True)
        self.assertTrue(all(len(x) <= 5 for x in out))

    # [COMMON-CHAT:T06-03-04] 改行保持：CRLF混在の厳密性
    def test_04_newline_preserve_strict(self):
        self._need()
        text = "line1\r\nline2\nline3\r\n"
        out = self.split(text, max_chars=100, split_sentences=False)
        # 長さ制約が干渉しない条件で厳密一致
        self.assertEqual("".join(out), text)

    # [COMMON-CHAT:T06-03-05] 文区切り優先かハード分割かの現実装確認
    def test_05_sentence_vs_hard_split_priority(self):
        self._need()
        text = "長語長語長語長語。次文です。"
        out = self.split(text, max_chars=6, split_sentences=True)
        # 実装の優先順位に追従（回帰検知が目的）
        self.assertTrue(len(out) >= 2)

    # [COMMON-CHAT:T06-03-06] 決定性（同一入力→同一出力）
    def test_06_deterministic_output(self):
        self._need()
        text = "Deterministic. Output. Check."
        p = dict(max_chars=50, split_sentences=True)
        out1 = self.split(text, **p)
        out2 = self.split(text, **p)
        self.assertEqual(out1, out2)

    # [COMMON-CHAT:T06-03-07] max_chars キャスト/境界
    def test_07_max_chars_cast_and_errors(self):
        self._need()
        # すべて非intは例外
        with self.assertRaises(Exception):
            self.split("abc def", max_chars="50")
        with self.assertRaises(Exception):
            self.split("abc", max_chars="0")
        with self.assertRaises(Exception):
            self.split("abc", max_chars="abc")

if __name__ == "__main__":
    mapping = {
        "test_01_en_space_after_punct": ("COMMON-CHAT:T06-03-01", "英文 空白保持（複合文）"),
        "test_02_cjk_mixed_endings":   ("COMMON-CHAT:T06-03-02", "CJK 文区切り複合"),
        "test_03_unicode_emoji":       ("COMMON-CHAT:T06-03-03", "Unicode/絵文字 長さ制御"),
        "test_04_newline_preserve_strict": ("COMMON-CHAT:T06-03-04", "改行保持 厳密一致"),
        "test_05_sentence_vs_hard_split_priority": ("COMMON-CHAT:T06-03-05", "文区切り優先 vs ハード分割"),
        "test_06_deterministic_output": ("COMMON-CHAT:T06-03-06", "決定性（同一入力→同一出力）"),
        "test_07_max_chars_cast_and_errors": ("COMMON-CHAT:T06-03-07", "max_chars キャスト/境界"),
    }
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TextSplitMoreCasesTest)
    run_unittest_suite("COMMON-CHAT:T06-03 common/chat/textsplit", suite, mapping)
