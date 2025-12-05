# -*- coding: utf-8 -*-
"""
T07-04 : Continuation internal guards (full cover)
対象: common.chat.continuation
- 例外ガードやフォールバック枝の網羅
"""

import unittest
from typing import Any, Dict, List
from unittest import mock

from tests._report import run_unittest_suite
from unittest.mock import patch
from common.chat import continuation as C  # type: ignore[import]

class ContinuationGuards2Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from common.chat import continuation as C  # type: ignore
        cls.C = C

    # [T07-04-01] _extract_tail_text: list サブクラスで __getitem__ 例外 → except 経路
    def test_01_extract_tail_text_exception(self):
        C = self.C

        class BadList(list):
            def __getitem__(self, idx):
                raise RuntimeError("boom")

        msgs = BadList(["x"])
        out = C._extract_tail_text(msgs)
        self.assertEqual(out, "")

    # [T07-04-02] _split_into_chunks: split_text が str を返す場合のフォールバック
    def test_02_split_into_chunks_result_str(self):
        C = self.C

        with mock.patch.object(C.textsplit, "split_text", return_value="XX"):  # type: ignore[attr-defined]
            out = C._split_into_chunks("ignored")
        self.assertEqual(out, ["XX"])

    # [T07-04-03] _split_into_chunks: split_text が未知型を返す場合のフォールバック（元テキストを 1 チャンク）
    def test_03_split_into_chunks_unknown_object(self):
        C = self.C

        class Dummy:
            pass

        with mock.patch.object(C.textsplit, "split_text", return_value=Dummy()):  # type: ignore[attr-defined]
            out = C._split_into_chunks("orig")
        self.assertEqual(out, ["orig"])

    # [T07-04-04] _split_into_chunks: text="" → 早期 return []
    def test_04_split_into_chunks_empty_text(self):
        C = self.C
        out = C._split_into_chunks("")
        self.assertEqual(out, [])

    # [T07-04-05] continue_chat: max_steps キャスト失敗 + reply.__str__ 例外 → responses 空の return ""
    def test_05_continue_chat_str_cast_raises_and_no_responses(self):
        C = self.C

        # split_text: 単一チャンクにする
        with mock.patch.object(C.textsplit, "split_text", return_value=["chunk"]):  # type: ignore[attr-defined]

            class BadStr:
                def __str__(self) -> str:
                    raise RuntimeError("boom-str")

            def fake_chat(*, messages, policy):
                # policy["max_steps"] が "x" のような非数値でも、
                # ここまで来た後は BadStr を返して str() 例外枝を通す
                return BadStr()

            out = C.continue_chat(
                messages=[{"role": "user", "content": "hello"}],
                policy={"max_steps": "x", "chat_fn": fake_chat},
            )

        # str() 例外で responses は最後まで空 → ""
        self.assertEqual(out, "")

    # [T07-04-06] _split_into_chunks: dict 形式だが "chunks" が list/tuple 以外の場合は空リスト
    @patch("common.chat.continuation.textsplit.split_text")
    def test_06_split_chunks_dict_chunks_non_sequence(self, mock_split) -> None:
        # split_text が {"chunks": "not-a-list"} を返すケース
        mock_split.return_value = {"chunks": "not-a-list"}

        # ★ ここを self.mod ではなく、モジュール C を直接使用
        chunks = C._split_into_chunks("abc")  # type: ignore[attr-defined]

        # raw が list/tuple ではないので chunks = [] が選ばれる
        self.assertEqual(chunks, [])


if __name__ == "__main__":
    mapping = {
        "test_01_extract_tail_text_exception": (
            "M02:T07-04-01",
            "_extract_tail_text: listサブクラスで__getitem__例外 → except経路",
        ),
        "test_02_split_into_chunks_result_str": (
            "M02:T07-04-02",
            "_split_into_chunks: split_textがstrを返す場合のフォールバック",
        ),
        "test_03_split_into_chunks_unknown_object": (
            "M02:T07-04-03",
            "_split_into_chunks: split_textが未知型を返す場合のフォールバック",
        ),
        "test_04_split_into_chunks_empty_text": (
            "M02:T07-04-04",
            "_split_into_chunks: text='' → 早期return[]",
        ),
        "test_05_continue_chat_str_cast_raises_and_no_responses": (
            "M02:T07-04-05",
            "continue_chat: max_stepsキャスト失敗 + reply.__str__例外 + responses空ガード",
        ),
       "test_06_split_chunks_dict_chunks_non_sequence": (
            "M02:T07-04-06",
            "_split_into_chunks: dict 形式だが \"chunks\" が list/tuple 以外の場合は空リスト",
        ),
    }
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ContinuationGuards2Test)
    run_unittest_suite("M02:T07-04 common/chat/continuation", suite, mapping)
