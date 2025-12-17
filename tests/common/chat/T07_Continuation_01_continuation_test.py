# -*- coding: utf-8 -*-
"""
T07-01 : Continuation Flow
対象: common.chat.continuation
- 履歴 + 入力 → メッセージ正規化 → chat_loop 経由で応答
- textsplit 連携、例外/上限、直呼び（policy.chat_fn）を網羅
"""

import unittest
from unittest.mock import patch, MagicMock
from tests._report import run_unittest_suite

def _load_targets():
    from common.chat import continuation as C  # type: ignore
    cont = getattr(C, "continue_chat", None) or getattr(C, "run", None)
    return C, cont


class ContinuationFlowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        mod, cont = _load_targets()
        cls.mod = mod
        cls.cont = staticmethod(cont)

    def _need(self):
        if not self.cont:
            self.skipTest("continue_chat not found")

    # [T07-01-01] 空コンテキスト
    @patch("common.chat.continuation.textsplit")
    @patch("common.chat.continuation.chat_loop")
    def test_01_empty_context(self, mock_loop, mock_split):
        self._need()
        mock_loop.chat.return_value = "（入力が空です）"
        mock_split.split_text.return_value = []
        out = self.cont(messages=[], policy={})
        self.assertTrue(isinstance(out, str))

    # [T07-01-02] 正常継続
    @patch("common.chat.continuation.textsplit")
    @patch("common.chat.continuation.chat_loop")
    def test_02_normal(self, mock_loop, mock_split):
        self._need()
        mock_loop.chat.return_value = "pong"
        mock_split.split_text.return_value = []
        out = self.cont(messages=[{"role":"user","content":"ping"}], policy={"provider":"openai","model":"gpt"})
        self.assertEqual(out, "pong")

    # [T07-01-03] 例外握り潰し
    @patch("common.chat.continuation.textsplit")
    @patch("common.chat.continuation.chat_loop")
    def test_03_provider_raises(self, mock_loop, mock_split):
        self._need()
        mock_loop.chat.side_effect = RuntimeError("boom")
        mock_split.split_text.return_value = []
        out = self.cont(messages=["hi"], policy={"provider":"openai","model":"gpt"})
        self.assertIsInstance(out, str)

    # [T07-01-04] 長文継続（分割）
    @patch("common.chat.continuation.textsplit")
    @patch("common.chat.continuation.chat_loop")
    def test_04_long_text_split(self, mock_loop, mock_split):
        self._need()
        mock_loop.chat.side_effect = ["part1", "part2"]
        mock_split.split_text.return_value = ["AAAA", "BBBB"]
        out = self.cont(messages=["X"*200], policy={"provider":"openai","model":"gpt"})
        self.assertTrue(out.endswith("part2"))

    # [T07-01-05] policy 直呼び
    @patch("common.chat.continuation.textsplit")
    def test_05_policy_direct_fn(self, mock_split):
        self._need()
        mock_split.split_text.return_value = []
        called = {"ok": False}

        def fake_chat(**kwargs):
            called["ok"] = True
            return "ok"

        out = self.cont(messages=["hello"], policy={"chat_fn": fake_chat, "provider":"x", "model":"m"})
        self.assertEqual(out, "ok")
        self.assertTrue(called["ok"])

    # [T07-01-06] メッセージ正規化が呼ばれる
    @patch("common.chat.continuation.message")
    @patch("common.chat.continuation.textsplit")
    @patch("common.chat.continuation.chat_loop")
    def test_06_message_normalize_called(self, mock_loop, mock_split, mock_msg):
        self._need()
        mock_loop.chat.return_value = "x"
        mock_split.split_text.return_value = []
        mock_msg.normalize_messages.return_value = [{"role":"user","content":"x"}]
        self.cont(messages="x", policy={"provider":"openai","model":"gpt"})
        mock_msg.normalize_messages.assert_called()

    # [T07-01-07] ステップ上限
    @patch("common.chat.continuation.textsplit")
    @patch("common.chat.continuation.chat_loop")
    def test_07_max_steps(self, mock_loop, mock_split):
        self._need()
        mock_loop.chat.return_value = "x"
        mock_split.split_text.return_value = ["a","b","c"]
        out = self.cont(messages=["x"], policy={"provider":"openai","model":"gpt", "max_steps":2})
        self.assertIsInstance(out, str)

    # [T07-01-08] None 応答
    @patch("common.chat.continuation.textsplit")
    @patch("common.chat.continuation.chat_loop")
    def test_08_none_reply(self, mock_loop, mock_split):
        self._need()
        mock_loop.chat.return_value = None
        mock_split.split_text.return_value = []
        out = self.cont(messages=["x"], policy={"provider":"openai","model":"gpt"})
        self.assertIsInstance(out, str)


if __name__ == "__main__":
    mapping = {
        "test_01_empty_context": ("COMMON-CHAT:T07-01-01", "空コンテキスト"),
        "test_02_normal": ("COMMON-CHAT:T07-01-02", "正常継続"),
        "test_03_provider_raises": ("COMMON-CHAT:T07-01-03", "例外握り潰し"),
        "test_04_long_text_split": ("COMMON-CHAT:T07-01-04", "長文継続（分割）"),
        "test_05_policy_direct_fn": ("COMMON-CHAT:T07-01-05", "policy 直呼び"),
        "test_06_message_normalize_called": ("COMMON-CHAT:T07-01-06", "メッセージ正規化呼び出し"),
        "test_07_max_steps": ("COMMON-CHAT:T07-01-07", "ステップ上限"),
        "test_08_none_reply": ("COMMON-CHAT:T07-01-08", "None 応答"),
    }
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ContinuationFlowTest)
    run_unittest_suite("COMMON-CHAT:T07-01 common\chat\continuation", suite, mapping)
