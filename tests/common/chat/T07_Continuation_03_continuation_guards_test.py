# -*- coding: utf-8 -*-
"""
T07-03 : Continuation Utility (guards & rare paths)
対象: common.chat.continuation

- policy 非 dict / None の扱い（_resolve_policy）
- messages が list 以外のときの末尾テキスト抽出（_extract_tail_text）
- textsplit.split_text の戻り値が「変則型」の場合の分岐（_split_into_chunks）
- _prepare_step_messages のガード経路（非 list / 非 dict / 非 str）
- continue_chat 内の max_steps キャスト例外、および str() 失敗時のガード
"""

import unittest
from typing import Any, Dict, List

from unittest import mock
from tests._report import run_unittest_suite


def _load_module():
    from common.chat import continuation as C  # type: ignore
    return C


class ContinuationGuardsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.C = _load_module()

    # [T07-03-01] _resolve_policy: None / 非 dict は空 dict に正規化
    def test_01_resolve_policy_none_and_invalid(self):
        C = self.C

        out_none = C._resolve_policy(None)
        self.assertIsInstance(out_none, dict)
        self.assertEqual(out_none, {})

        out_str = C._resolve_policy("not-dict")  # type: ignore[arg-type]
        self.assertIsInstance(out_str, dict)
        self.assertEqual(out_str, {})

    # [T07-03-02] _extract_tail_text: list 以外の入力は空文字
    def test_02_extract_tail_text_non_list(self):
        C = self.C

        out = C._extract_tail_text("hello")  # list ではない
        self.assertEqual(out, "")

    # [T07-03-03] _split_into_chunks: split_text の戻り値が dict / list / その他
    def test_03_split_into_chunks_various_result_types(self):
        C = self.C

        # 1) dict 形式: {"chunks": [...]} から非 str / 空文字を除去して採用
        with mock.patch.object(C.textsplit, "split_text", return_value={"chunks": ["a", "", None, "b"]}):
            chunks = C._split_into_chunks("ignored")
            self.assertEqual(chunks, ["a", "b"])

        # 2) list/tuple 形式: 非 str / 空文字をスキップ
        with mock.patch.object(C.textsplit, "split_text", return_value=("x", "", 123, "y")):
            chunks = C._split_into_chunks("ignored")
            self.assertEqual(chunks, ["x", "y"])

        # 3) 予期しない型: 元テキスト全体を 1 チャンクとして扱う
        with mock.patch.object(C.textsplit, "split_text", return_value=123):
            chunks = C._split_into_chunks("base-text")
            self.assertEqual(chunks, ["base-text"])

    # [T07-03-04] _prepare_step_messages: list 以外 / 非 dict 末尾要素のパス
    def test_04_prepare_step_messages_guards(self):
        C = self.C

        # base_messages が list でない場合 → [chunk] のみ
        out_non_list = C._prepare_step_messages("not-a-list", "chunk")
        self.assertEqual(out_non_list, ["chunk"])

        # 空 list の場合 → [chunk] のみ
        out_empty = C._prepare_step_messages([], "chunk")
        self.assertEqual(out_empty, ["chunk"])

        # 末尾要素が dict でも str でもない場合 → そのまま + chunk 追加
        base = [{"role": "user", "content": "keep"}, 123]
        out_mixed = C._prepare_step_messages(base, "added")
        self.assertEqual(out_mixed[-1], "added")
        self.assertIn({"role": "user", "content": "keep"}, out_mixed)

    # [T07-03-05] continue_chat: max_steps キャスト例外 + str() 例外経路
    def test_05_continue_chat_max_steps_cast_and_str_error(self):
        C = self.C

        # __str__ が例外を投げるオブジェクト
        class BadRepr:
            def __str__(self) -> str:  # pragma: no cover - 例外パスのみ
                raise RuntimeError("boom")

        calls: List[Dict[str, Any]] = []

        def fake_chat(*, messages, policy):
            # 呼び出しはされるが、返り値は文字列化に失敗するオブジェクト
            calls.append({"messages": messages, "policy": policy})
            return BadRepr()

        policy = {
            "chat_fn": fake_chat,
            "provider": "x",
            "model": "y",
            # int() 変換に失敗する値を入れて、except 経路を通す
            "max_steps": "not-a-number",
        }

        out = C.continue_chat(messages=["hello"], policy=policy)

        # 文字列化に失敗したため、responses は空 → 出力は空文字
        self.assertEqual(out, "")
        # fake_chat 自体は 1 回は呼ばれている想定
        self.assertGreaterEqual(len(calls), 1)


if __name__ == "__main__":
    mapping = {
        "test_01_resolve_policy_none_and_invalid": (
            "M02:T07-03-01",
            "policy None / 非dict を空 dict に正規化（_resolve_policy）",
        ),
        "test_02_extract_tail_text_non_list": (
            "M02:T07-03-02",
            "messages が list 以外の場合は末尾テキスト抽出結果が空文字（_extract_tail_text）",
        ),
        "test_03_split_into_chunks_various_result_types": (
            "M02:T07-03-03",
            "split_text の戻り値が dict / list / その他の各分岐カバー（_split_into_chunks）",
        ),
        "test_04_prepare_step_messages_guards": (
            "M02:T07-03-04",
            "base_messages が list 以外 / 空 list / 非dict末尾の各ガード分岐（_prepare_step_messages）",
        ),
        "test_05_continue_chat_max_steps_cast_and_str_error": (
            "M02:T07-03-05",
            "max_steps キャスト失敗と reply の str() 例外ガード（continue_chat 本体）",
        ),
    }
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ContinuationGuardsTest)
    run_unittest_suite("M02:T07-03 common/chat/continuation", suite, mapping)
