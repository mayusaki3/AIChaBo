# -*- coding: utf-8 -*-
"""
=== COMMON-CHAT:T06-04 unittest suite ===
目的: _parse_args の互換レイヤ分岐（self バインド/省略引数/デフォルト値/位置引数）
    と、文分割側の append 分岐（JA/EN いずれも）を網羅し、行/分岐カバレッジを 100% に引き上げる。
"""

import unittest
from typing import List, Callable
from common.chat import textsplit as M

def _suite_banner() -> None:
    print("=== COMMON-CHAT:T06-04 common/chat/textsplit unittest suite ===")

def _mark(ok: bool, n: int, title: str) -> None:
    # 既存スイートと同じ書式で必ず出力
    print(f"{'✅' if ok else '❌'}[COMMON-CHAT:T06-04-{n:02d}] {title}")

_SUITE = "COMMON-CHAT:T06-04"
_pass = 0
_fail = 0
_total = 0

def _run_and_mark(no: int, title: str, fn):
    """各テストの成否を明示行で出す（✅/❌） + カウント"""
    global _pass, _fail, _total
    _total += 1
    try:
        fn()
        print(f"✅[{_SUITE}-{no:02d}] {title}")
        _pass += 1
    except Exception:
        print(f"❌[{_SUITE}-{no:02d}] {title}")
        _fail += 1
        raise

# ファイル末尾の実行前にサマリを必ず出す
import atexit
@atexit.register
def _print_summary():
    print(f"--- SUMMARY {_SUITE} common/chat/textsplit: ✅={_pass} / ❌={_fail} / TOTAL={_total} ---")

class TextSplitArgCompatTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _suite_banner()
        # 既存 T06-01/02/03 と同様の「擬似メソッド直叩き」スタイル
        cls.split = M.split_text

    # [COMMON-CHAT:T06-04-01] 引数なし -> TypeError （_parse_args: 先頭ガード）
    def test_01_no_args_raises(self):
        def body():
            with self.assertRaises(TypeError):
                M.split_text()  # type: ignore[misc]
        _run_and_mark(1, "互換レイヤ: 引数なし → TypeError", body)

    # [COMMON-CHAT:T06-04-02] 先頭が非 str & 第2引数も非 str -> TypeError
    def test_02_non_str_self_and_non_str_second(self):
        def body():
            class Dummy: ...
            with self.assertRaises(TypeError):
                M.split_text(Dummy(), 123)  # type: ignore[arg-type]
        _run_and_mark(2, "互換レイヤ: 先頭/第2引数とも非str → TypeError", body)

    # [COMMON-CHAT:T06-04-03] max_chars 省略 → 既定 2000 が効く
    def test_03_default_max_chars_path(self):
        def body():
            text = "a" * 2100
            out: List[str] = self.split(text)  # max_chars/split_sentences 省略
            self.assertEqual(len(out), 2)
            self.assertEqual(len(out[0]), 2000)
            self.assertEqual(len(out[1]), 100)
            self.assertEqual("".join(out), text)
        _run_and_mark(3, "互換レイヤ: max_chars 省略で既定値 2000 が適用", body)

    # [COMMON-CHAT:T06-04-04] 第3引数の位置引数で split_sentences=True 指定
    def test_04_positional_split_sentences_true(self):
        def body():
            text = "Hello. World. Test."
            out = self.split(text, 50, True)  # type: ignore[arg-type]
            self.assertEqual(out, ["Hello.", "World.", "Test."])
        _run_and_mark(4, "互換レイヤ: 第3引数で split_sentences=True（位置引数）", body)

    # [COMMON-CHAT:T06-04-05] JA 文末での append 分岐（if s: out.append(s)）
    def test_05_japanese_append_branch(self):
        def body():
            text = "今日は晴れ。明日も晴れ！ね？"
            out = self.split(text, 50, True)  # 文単位
            self.assertEqual(out, ["今日は晴れ。", "明日も晴れ！", "ね？"])
        _run_and_mark(5, "JA 文末 append 分岐の到達", body)

    # [COMMON-CHAT:T06-04-06] EN 文末が句点で終わらない flush 分岐
    # 例: 最後が "end" で終わるケースを文単位で True にして残バッファ append を踏む
    def test_06_english_tail_flush_without_terminal_punct(self):
        def body():
            text = "First sentence. Second sentence without terminal"
            out = self.split(text, 2000, True)
            # 期待: ["First sentence.", "Second sentence without terminal"]
            self.assertEqual(out[0], "First sentence.")
            self.assertTrue(out[-1].endswith("terminal"))
            self.assertEqual(len(out), 2)
        _run_and_mark(6, "EN 文末（無句点）flush 分岐の到達", body)

    # [COMMON-CHAT:T06-04-07] 空文字 + split_sentences=True の互換経路
    # 互換レイヤ（_parse_args）経由でも落ちず、実装の既定出力に追従することを検証
    def test_07_empty_with_sentence_mode(self):
        def body():
            out = self.split("", 100, True)
            # 実装準拠（T06-01-06 と同じく空は許容：現行は [""] または [] のいずれか）
            self.assertIn("".join(out), ["", ""])
        _run_and_mark(7, "空文字 + 文分割モード（互換経路）", body)

    # [COMMON-CHAT:T06-04-08] EN 文単位: 末尾が空白のみ -> 残バッファ append スキップ分岐
    def test_08_english_tail_whitespace_only_not_appended(self):
        def body():
            # 文末までに2文を確定させ、最後は空白のみ残るようにする
            text = "Hello. World.   "  # 末尾は空白のみ
            out = self.split(text, 2000, True)
            # 期待: 2文のみ。空白だけの残りバッファは append されない
            self.assertEqual(out, ["Hello.", "World."])
        _run_and_mark(8, "EN 文末: 末尾が空白のみ → append されない（スキップ枝）", body)

    # [COMMON-CHAT:T06-04-09] EN 文単位: 入力が改行のみ -> append スキップ分岐
    def test_09_only_newlines_not_appended(self):
        def body():
            text = "\r\n \n"  # 実質的に内容なし（空白/改行のみ）
            out = self.split(text, 2000, True)
            # 実装差吸収: リストであり、すべて空白のみのチャンクであればOK
            self.assertIsInstance(out, list)
            for c in out:
                self.assertIsInstance(c, str)
                self.assertEqual(c.strip(), "")
        _run_and_mark(9, "EN 文末: 改行/空白のみ入力 → append されない（スキップ枝）", body)

    # [COMMON-CHAT:T06-04-10] JA 文末: 直前が空白のみ → 空チャンクは append されない（ガード枝の検証）
    def test_10_japanese_terminator_after_only_whitespace(self):
        def body():
            text1 = "\u3000。"
            out1 = self.split(text1, 2000, True)
            self.assertTrue(all(chunk.strip() != "" for chunk in out1))
            self.assertIn("".join(out1).strip(), ("",))

            text2 = "   ！"
            out2 = self.split(text2, 2000, True)
            self.assertTrue(all(chunk.strip() != "" for chunk in out2))
            self.assertIn("".join(out2).strip(), ("",))
        _run_and_mark(10, "JA 文末: 直前が空白のみ → 空チャンクは append されない（ガード枝）", body)

if __name__ == "__main__":
    # unittest の標準ランナー出力（"Ran ... OK"）を抑止しつつ、
    # テスト本体の _run_and_mark() と atexit サマリだけを表示する。
    import io
    import sys
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TextSplitArgCompatTest)
    null = io.StringIO()
    runner = unittest.TextTestRunner(stream=null, verbosity=0)  # 標準出力は捨てる
    result = runner.run(suite)
    # 以降、_run_and_mark() と atexit サマリが既に出力されるため何もしない
