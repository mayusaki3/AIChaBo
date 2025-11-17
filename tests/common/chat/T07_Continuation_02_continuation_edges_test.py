# -*- coding: utf-8 -*-
"""
M02:T07-02 unittest suite

目的:
- continuation の境界条件（max_steps=0、空チャンク、textsplit 例外 など）の動作確認

対象:
- common/chat/continuation.py
"""

import unittest
from unittest.mock import patch
from tests._report import run_unittest_suite

def _load_targets():
    from common.chat import continuation as C  # type: ignore
    return C, C.continue_chat

class ContinuationEdgesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod, cls.cont = _load_targets()

    @patch("common.chat.continuation.chat_loop")
    def test_01_max_steps_zero(self, mock_chat_loop):
        # [M02:T07-02-01] max_steps=0 → chat_loop 呼ばれない
        mock_chat_loop.chat.return_value = "ok"
        _ = self.cont(messages=["x"], policy={"provider":"p","model":"m","max_steps":0})
        self.assertEqual(mock_chat_loop.chat.call_count, 0)

    @patch("common.chat.continuation.chat_loop")
    def test_02_empty_chunks(self, mock_chat_loop):
        # [M02:T07-02-02] 空文字のみ → 呼ばれない
        mock_chat_loop.chat.return_value = "ok"
        _ = self.cont(messages=[""], policy={"provider":"p","model":"m"})
        self.assertEqual(mock_chat_loop.chat.call_count, 0)

    @patch("common.chat.continuation.textsplit")
    @patch("common.chat.continuation.chat_loop")
    def test_03_textsplit_raises(self, mock_chat_loop, mock_textsplit):
        # [M02:T07-02-03] textsplit 例外 → 呼ばれない
        mock_chat_loop.chat.return_value = "ok"
        mock_textsplit.split_text.side_effect = RuntimeError("boom")
        _ = self.cont(messages=["abc"], policy={"provider":"p","model":"m"})
        self.assertEqual(mock_chat_loop.chat.call_count, 0)

    @patch("common.chat.continuation.chat_loop")
    def test_04_none_policy(self, mock_chat_loop):
        # [M02:T07-02-04] policy=None でも落ちない
        mock_chat_loop.chat.return_value = None
        out = self.cont(messages=["x"], policy=None)
        self.assertIsInstance(out, str)

    @patch("common.chat.continuation.chat_loop")
    def test_05_runs_once(self, mock_chat_loop):
        # [M02:T07-02-05] 単一チャンク → 1 回だけ呼ばれる
        mock_chat_loop.chat.return_value = "ok"
        _ = self.cont(messages=["ok"], policy={"provider":"p","model":"m"})
        self.assertEqual(mock_chat_loop.chat.call_count, 1)


if __name__ == "__main__":
    mapping = {
        "test_01_max_steps_zero": ("M02:T07-02-01", "max_steps=0 → 呼ばれない"),
        "test_02_empty_chunks": ("M02:T07-02-02", "空チャンク → 呼ばれない"),
        "test_03_textsplit_raises": ("M02:T07-02-03", "textsplit 例外 → 呼ばれない"),
        "test_04_none_policy": ("M02:T07-02-04", "policy=None でも落ちない"),
        "test_05_runs_once": ("M02:T07-02-05", "単一チャンクは1回呼び出し"),
    }
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ContinuationEdgesTest)
    run_unittest_suite("M02:T07-02", suite, mapping)
