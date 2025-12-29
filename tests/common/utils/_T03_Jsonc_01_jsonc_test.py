# -*- coding: utf-8 -*-
"""
COMMON-UTILS:T03 : jsonc

対象: common.utils.jsonc

目的:
- JSONC（//, #, /*...*/ コメント）を除去して JSON として loads できること
- 文字列中の疑似コメント（"//" 等）は保持されること
- 末尾カンマ（trailing comma）が文字列外で除去されること
- load_jsonc が UTF-8 読み取りで動作すること

テスト番号:
- COMMON-UTILS:T03-01-01 ...（T03=jsonc, 01=テストコード, 01..=ケース）

実行:
- python -m tests.common.utils.T03_Jsonc_01_jsonc_test
"""

import tempfile
import unittest
from pathlib import Path
from typing import Dict, Tuple

from tests._report import run_unittest_suite


class JsoncTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from common.utils import jsonc as mod  # type: ignore
        cls.mod = mod

    # [COMMON-UTILS:T03-01-01] // コメント除去 + 読み込み
    def test_01_loads_jsonc_line_comment_slashslash(self):
        s = """
        {
          // comment
          "a": 1
        }
        """
        obj = self.mod.loads_jsonc(s)
        self.assertEqual(obj["a"], 1)

    # [COMMON-UTILS:T03-01-02] # コメント除去 + 読み込み
    def test_02_loads_jsonc_line_comment_hash(self):
        s = """
        {
          # comment
          "a": 1
        }
        """
        obj = self.mod.loads_jsonc(s)
        self.assertEqual(obj["a"], 1)

    # [COMMON-UTILS:T03-01-03] /*...*/ コメント除去 + 読み込み
    def test_03_loads_jsonc_block_comment(self):
        s = """
        {
          /* block
             comment */
          "a": 1
        }
        """
        obj = self.mod.loads_jsonc(s)
        self.assertEqual(obj["a"], 1)

    # [COMMON-UTILS:T03-01-04] 文字列内の // や /* */ は除去されない
    def test_04_string_contains_comment_markers_kept(self):
        s = r"""
        {
          "url": "https://example.com/a//b",
          "x": "not /* a */ comment",
          "y": "escaped quote: \" // still in string"
        }
        """
        obj = self.mod.loads_jsonc(s)
        self.assertEqual(obj["url"], "https://example.com/a//b")
        self.assertEqual(obj["x"], "not /* a */ comment")
        self.assertIn("// still in string", obj["y"])

    # [COMMON-UTILS:T03-01-05] 末尾カンマ除去（object/array）
    def test_05_trailing_commas_removed(self):
        s = """
        {
          "a": 1,
          "b": [1, 2, 3,],
          "c": {"x": 1,},
        }
        """
        obj = self.mod.loads_jsonc(s)
        self.assertEqual(obj["a"], 1)
        self.assertEqual(obj["b"], [1, 2, 3])
        self.assertEqual(obj["c"], {"x": 1})

    # [COMMON-UTILS:T03-01-06] 末尾カンマ: 文字列内は除去されない
    def test_06_trailing_comma_in_string_kept(self):
        s = r"""
        {
          "a": "x,}",
          "b": "y,]"
        }
        """
        obj = self.mod.loads_jsonc(s)
        self.assertEqual(obj["a"], "x,}")
        self.assertEqual(obj["b"], "y,]")

    # [COMMON-UTILS:T03-01-07] loads_jsonc: 不正JSONは例外
    def test_07_invalid_json_raises(self):
        s = "{ not json"
        with self.assertRaises(Exception):
            _ = self.mod.loads_jsonc(s)

    # [COMMON-UTILS:T03-01-08] load_jsonc: ファイル読み取り（utf-8）
    def test_08_load_jsonc_reads_file_utf8(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "a.jsonc"
            p.write_text('{"a": 1, /*c*/ "b": 2}', encoding="utf-8")
            obj = self.mod.load_jsonc(str(p))
            self.assertEqual(obj, {"a": 1, "b": 2})

    # [COMMON-UTILS:T03-01-09] 内部: strip関数が str を返し、改行維持しても落ちない
    def test_09_strip_returns_str(self):
        s = "{\n  // x\n  \"a\": 1,\n}\n"
        out = self.mod._strip_comments_and_trailing_commas(s)  # type: ignore[attr-defined]
        self.assertIsInstance(out, str)
        self.assertIn('"a": 1', out)


if __name__ == "__main__":
    mapping: Dict[str, Tuple[str, str]] = {
        "test_01_loads_jsonc_line_comment_slashslash": ("COMMON-UTILS:T03-01-01", "// コメント除去"),
        "test_02_loads_jsonc_line_comment_hash": ("COMMON-UTILS:T03-01-02", "# コメント除去"),
        "test_03_loads_jsonc_block_comment": ("COMMON-UTILS:T03-01-03", "/*...*/ コメント除去"),
        "test_04_string_contains_comment_markers_kept": ("COMMON-UTILS:T03-01-04", "文字列内の疑似コメントは保持"),
        "test_05_trailing_commas_removed": ("COMMON-UTILS:T03-01-05", "末尾カンマ除去（object/array）"),
        "test_06_trailing_comma_in_string_kept": ("COMMON-UTILS:T03-01-06", "文字列内の末尾カンマは保持"),
        "test_07_invalid_json_raises": ("COMMON-UTILS:T03-01-07", "不正JSONは例外"),
        "test_08_load_jsonc_reads_file_utf8": ("COMMON-UTILS:T03-01-08", "load_jsonc: utf-8 ファイル読み取り"),
        "test_09_strip_returns_str": ("COMMON-UTILS:T03-01-09", "_strip_* は str を返す"),
    }
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(JsoncTest)
    run_unittest_suite("COMMON-UTILS:T03 common/utils/jsonc", suite, mapping)
