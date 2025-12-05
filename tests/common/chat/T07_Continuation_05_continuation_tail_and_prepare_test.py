# -*- coding: utf-8 -*-
"""
T07-05 : Continuation tail & prepare guards
対象: common.chat.continuation
- _extract_tail_text の残り分岐（末尾が str / 非dict・非str）
- _prepare_step_messages の想定外末尾型 / 非listベースのガード経路
"""

import unittest
from typing import Any, Dict, List

from tests._report import run_unittest_suite
from unittest.mock import patch

class ContinuationTailAndPrepareGuardsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # テスト対象モジュールを一度だけ import
        from common.chat import continuation as C  # type: ignore
        cls.mod = C

    # [T07-05-01] _extract_tail_text: 末尾が str の場合にその文字列を返す
    def test_01_extract_tail_last_is_str(self):
        text = "hello tail"
        messages: List[Any] = ["ignore", text]

        out = self.mod._extract_tail_text(messages)  # type: ignore[attr-defined]
        self.assertEqual(out, text)

    # [T07-05-02] _extract_tail_text: 末尾が dict/str 以外の場合は最終 return "" 経路
    def test_02_extract_tail_last_is_unknown_type(self):
        messages: List[Any] = [
            {"role": "user", "content": "ok"},
            123,  # dict/str 以外
        ]

        out = self.mod._extract_tail_text(messages)  # type: ignore[attr-defined]
        self.assertEqual(out, "")

    # [T07-05-03] _prepare_step_messages: 末尾が想定外型の場合は末尾に chunk を append
    def test_03_prepare_step_messages_unknown_last_type(self):
        base_messages: List[Any] = [
            {"role": "user", "content": "keep"},
            123,  # 想定外型
        ]
        chunk = "next-chunk"

        out = self.mod._prepare_step_messages(base_messages, chunk)  # type: ignore[attr-defined]

        # 先頭はそのまま / 想定外型も残り、末尾に chunk が追加される
        self.assertEqual(len(out), 3)
        self.assertEqual(out[0]["content"], "keep")
        self.assertEqual(out[1], 123)
        self.assertEqual(out[2], chunk)

    # [T07-05-04] _prepare_step_messages: base_messages が非listの場合のガード経路
    def test_04_prepare_step_messages_base_not_list(self):
        base_messages: Any = "not-a-list"
        chunk = "only-chunk"

        out = self.mod._prepare_step_messages(base_messages, chunk)  # type: ignore[attr-defined]
        self.assertEqual(out, [chunk])

    # [T07-05-05] _prepare_step_messages: base_messages が空 list の場合のガード経路
    def test_05_prepare_step_messages_base_empty_list(self):
        base_messages: List[Any] = []
        chunk = "only-chunk"

        out = self.mod._prepare_step_messages(base_messages, chunk)  # type: ignore[attr-defined]
        self.assertEqual(out, [chunk])


if __name__ == "__main__":
    mapping: Dict[str, tuple[str, str]] = {
        "test_01_extract_tail_last_is_str": (
            "M02:T07-05-01",
            "_extract_tail_text: 末尾が str の場合にその文字列を返す",
        ),
        "test_02_extract_tail_last_is_unknown_type": (
            "M02:T07-05-02",
            "_extract_tail_text: 末尾が dict/str 以外の場合は空文字を返すガード経路",
        ),
        "test_03_prepare_step_messages_unknown_last_type": (
            "M02:T07-05-03",
            "_prepare_step_messages: 末尾が想定外型の場合に末尾へ chunk を append",
        ),
        "test_04_prepare_step_messages_base_not_list": (
            "M02:T07-05-04",
            "_prepare_step_messages: base_messages が list 以外の場合のガード経路",
        ),
        "test_05_prepare_step_messages_base_empty_list": (
            "M02:T07-05-05",
            "_prepare_step_messages: base_messages が空 list の場合のガード経路",
        ),
    }

    suite = unittest.defaultTestLoader.loadTestsFromTestCase(
        ContinuationTailAndPrepareGuardsTest
    )
    run_unittest_suite("M02:T07-05 common/chat/continuation", suite, mapping)
