# -*- coding: utf-8 -*-
"""
T04-06 : ChatLoop ルート網羅（helpers/normalize/dispatch 仕上げ）

対象: common/chat/chat_loop.py

目的:
  - T04-01〜05 で未到達だった「方針解決〜実行」の軽微な分岐を最小入力でカバーする。
  - 現行実装 (async def run(provider, context_list, user_id, guild_id, model=None)) に厳密に追従する。
検証観点:
  - 明示 model 引数が policy より優先される
  - model 未指定時に policy の model を使用する
  - 非文字列応答を str 化する
  - 空文字応答を「（応答が空でした）」にマップする
  - プロバイダ呼び出し側で例外が出た場合に「（チャット実行でエラーが発生しました）」を返す
実行例:
  coverage run -a -m tests.T04_ChatLoop_06_chat_loop_paths_cover_test
"""

import asyncio
import unittest
from unittest.mock import patch, AsyncMock

from tests._report import run_unittest_suite  # 共通レポータ
from common.chat import chat_loop


class ChatLoopPathsCoverTest(unittest.TestCase):
    """
    ChatLoop.run の「最終モデル決定」「応答整形」「例外処理」の枝を埋めるテスト群。
    既存 T04-01..05 と重複しないよう、以下にフォーカスする:
      - final_model の決定ロジック
      - 応答型/内容に応じた整形
      - provider 側例外時のフォールバック
    """

    # [T04-06-01]
    # 明示 model 引数が policy の model を上書きして provider 呼び出しに渡ること。
    def test_01_explicit_model_overrides_policy_model(self):
        async_mock = AsyncMock(return_value="ok")

        with patch("common.chat.chat_loop._extract_chat_policy_from_sessions",
                   return_value={"model": "from_policy"}), \
             patch("common.chat.chat_loop._resolve_api_key",
                   return_value="DUMMY_KEY"), \
             patch("common.chat.chat_loop._get_provider_chat_fn",
                   return_value=async_mock):

            out = asyncio.run(chat_loop.run(
                "openai",
                ["hello"],
                user_id=1,
                guild_id=2,
                model="explicit-model",
            ))

            self.assertEqual(out, "ok")
            async_mock.assert_awaited_once()
            _, kwargs = async_mock.call_args
            # 明示指定が優先されていること
            self.assertEqual(kwargs.get("model"), "explicit-model")

    # [T04-06-02]
    # model 未指定時、policy の model が使用されること。
    def test_02_model_filled_from_policy_when_missing(self):
        async_mock = AsyncMock(return_value="ok")

        with patch("common.chat.chat_loop._extract_chat_policy_from_sessions",
                   return_value={"model": "from_policy"}), \
             patch("common.chat.chat_loop._resolve_api_key",
                   return_value="DUMMY_KEY"), \
             patch("common.chat.chat_loop._get_provider_chat_fn",
                   return_value=async_mock):

            out = asyncio.run(chat_loop.run(
                "openai",
                ["hi"],
                user_id=1,
                guild_id=2,
                model=None,
            ))

            self.assertEqual(out, "ok")
            async_mock.assert_awaited_once()
            _, kwargs = async_mock.call_args
            self.assertEqual(kwargs.get("model"), "from_policy")

    # [T04-06-03]
    # provider 応答が非文字列の場合、str() で文字列化して返すこと。
    def test_03_non_string_reply_is_converted_to_str(self):
        async_mock = AsyncMock(return_value={"msg": "ok"})

        with patch("common.chat.chat_loop._extract_chat_policy_from_sessions",
                   return_value={"model": "m"}), \
             patch("common.chat.chat_loop._resolve_api_key",
                   return_value="KEY"), \
             patch("common.chat.chat_loop._get_provider_chat_fn",
                   return_value=async_mock):

            out = asyncio.run(chat_loop.run(
                "openai",
                ["hello"],
                user_id=1,
                guild_id=2,
            ))

            self.assertEqual(out, "{'msg': 'ok'}")

    # [T04-06-04]
    # provider 応答が空文字/偽値の場合、「（応答が空でした）」に置き換えること。
    def test_04_empty_reply_becomes_fixed_message(self):
        async_mock = AsyncMock(return_value="")

        with patch("common.chat.chat_loop._extract_chat_policy_from_sessions",
                   return_value={"model": "m"}), \
             patch("common.chat.chat_loop._resolve_api_key",
                   return_value="KEY"), \
             patch("common.chat.chat_loop._get_provider_chat_fn",
                   return_value=async_mock):

            out = asyncio.run(chat_loop.run(
                "openai",
                ["hello"],
                user_id=1,
                guild_id=2,
            ))

            self.assertEqual(out, "（応答が空でした）")

    # [T04-06-05]
    # provider 側で例外発生時、「（チャット実行でエラーが発生しました）」にフォールバックすること。
    def test_05_provider_raises_returns_error_message(self):
        async def boom(*args, **kwargs):
            raise RuntimeError("boom")

        with patch("common.chat.chat_loop._extract_chat_policy_from_sessions",
                   return_value={"model": "m"}), \
             patch("common.chat.chat_loop._resolve_api_key",
                   return_value="KEY"), \
             patch("common.chat.chat_loop._get_provider_chat_fn",
                   return_value=boom):

            out = asyncio.run(chat_loop.run(
                "openai",
                ["hello"],
                user_id=1,
                guild_id=2,
            ))

            self.assertEqual(out, "（チャット実行でエラーが発生しました）")


if __name__ == "__main__":
    mapping = {
        "test_01_explicit_model_overrides_policy_model":
            ("M02:T04-06-01", "explicit model overrides policy model"),
        "test_02_model_filled_from_policy_when_missing":
            ("M02:T04-06-02", "model from policy when missing"),
        "test_03_non_string_reply_is_converted_to_str":
            ("M02:T04-06-03", "non-str reply -> str()"),
        "test_04_empty_reply_becomes_fixed_message":
            ("M02:T04-06-04", "empty reply -> （応答が空でした）"),
        "test_05_provider_raises_returns_error_message":
            ("M02:T04-06-05", "provider raises -> error message"),
    }
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ChatLoopPathsCoverTest)
    run_unittest_suite("M02:T04-06 common/chat/chat_loop", suite, mapping)
