# -*- coding: utf-8 -*-
"""
T07-06 : Continuation top-level guards
対象: common.chat.continuation

目的:
- continue_chat の「トップレベルガード」経路を網羅する
  - tail_text が空の場合に早期 return し、chat_fn が呼ばれない
  - _split_into_chunks が None を返す場合に早期 return し、chat_fn が呼ばれない
"""

import unittest
from typing import Any, Dict, List
from unittest.mock import Mock, patch

from tests._report import run_unittest_suite


class ContinuationTopLevelGuardsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # テスト対象モジュールを一度だけ import
        from common.chat import continuation as C  # type: ignore
        cls.mod = C

    # [T07-06-01] tail_text が空の場合は早期 return "" し、chat_fn は呼ばれない
    def test_01_continue_chat_tail_text_empty_early_return(self):
        # content を持たない dict 末尾 → _extract_tail_text が "" を返す想定
        messages: List[dict[str, Any]] = [
            {"role": "user"},  # content 無し
        ]

        mock_chat = Mock(return_value="SHOULD_NOT_BE_CALLED")
        policy: Dict[str, Any] = {
            "chat_fn": mock_chat,
            # max_steps 等は指定しない（デフォルト動作）
        }

        out = self.mod.continue_chat(messages=messages, policy=policy)  # type: ignore[attr-defined]

        self.assertEqual(out, "")
        mock_chat.assert_not_called()

    # [T07-06-02] _split_into_chunks が None（内部で textsplit 例外）を返した場合、
    #             chat_fn は呼ばれず、結果は "" になる
    @patch("common.chat.continuation.textsplit.split_text")
    def test_02_continue_chat_split_returns_none(self, mock_split):
        # textsplit.split_text が例外を投げる → _split_into_chunks が None を返す経路
        mock_split.side_effect = RuntimeError("boom")

        messages: List[dict[str, Any]] = [
            {"role": "user", "content": "abc"},
        ]

        mock_chat = Mock(return_value="SHOULD_NOT_BE_CALLED")
        policy: Dict[str, Any] = {
            "chat_fn": mock_chat,
            # max_steps 等は指定しない（デフォルト動作）
        }

        out = self.mod.continue_chat(messages=messages, policy=policy)  # type: ignore[attr-defined]

        self.assertEqual(out, "")
        mock_chat.assert_not_called()

    # [T07-06-03] 非文字列応答の __str__ 正常経路で responses に追加される
    @patch("common.chat.continuation.textsplit.split_text")
    def test_03_non_string_reply_str_success(self, mock_split) -> None:
        # 1 チャンクだけ返すようにしておく
        mock_split.return_value = ["chunk-1"]

        class DummyReply:
            """__str__ が正常に文字列を返す非文字列オブジェクト"""

            def __str__(self) -> str:
                return "DUMMY-OK"

        calls: List[Any] = []

        def dummy_chat(*, messages: Any, policy: Dict[str, Any]) -> Any:
            # 非文字列オブジェクトを返す
            calls.append(messages)
            return DummyReply()

        messages: List[Dict[str, Any]] = [
            {"role": "user", "content": "original text"},
        ]

        out = self.mod.continue_chat(
            messages=messages,
            policy={"chat_fn": dummy_chat, "max_steps": 1},
        )

        # __str__ 正常経路で "DUMMY-OK" が responses に追加され、結合結果として返る
        self.assertEqual(out, "DUMMY-OK")
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    mapping: Dict[str, tuple[str, str]] = {
        "test_01_continue_chat_tail_text_empty_early_return": (
            "COMMON-CHAT:T07-06-01",
            "tail_text が空の場合は早期 return \"\" し、chat_fn は呼ばれない",
        ),
        "test_02_continue_chat_split_returns_none": (
            "COMMON-CHAT:T07-06-02",
            "_split_into_chunks が None を返す場合に chat_fn を呼ばず \"\" を返す",
        ),
        "test_03_non_string_reply_str_success": (
            "COMMON-CHAT:T07-06-03",
            "非文字列応答の __str__ 正常経路で responses に追加される",
        ),
    }

    suite = unittest.defaultTestLoader.loadTestsFromTestCase(
        ContinuationTopLevelGuardsTest
    )
    run_unittest_suite(
        "COMMON-CHAT:T07-06 common/chat/continuation",
        suite,
        mapping,
    )
