# T05-04 : ChatLoop cover rest branches
# 狙い: chat_loop.py の未到達(14–27, 34–43, 51–59, 101)をコード変更なしでテスト到達
# 実行: python -m utiltests.T05_ChatLoop_04_chat_loop_cover_rest_test

import asyncio
import unittest
from unittest.mock import patch
from utiltests._report import run_unittest_suite
from common.chat.chat_loop import run as chat_run

MSG_PROVIDER_ERROR = "（チャット実行でエラーが発生しました）"

class ChatLoopCoverRestTest(unittest.TestCase):
    def test_01_provider_trim_and_upper_is_valid(self):
        """provider が '  OPENAI  ' でも有効として通ること（前処理枝）"""
        async def fake_ok(context_list, api_key, model=None, **extra):
            return "ok"
        with patch("common.chat.chat_loop._extract_chat_policy_from_sessions",
                   return_value={"model": "m"}), \
             patch("common.chat.chat_loop._resolve_api_key",
                   return_value="KEY"), \
             patch("common.chat.chat_loop._get_provider_chat_fn",
                   return_value=fake_ok):
            out = asyncio.run(chat_run(
                provider="  OPENAI  ",
                context_list=["hello"],
                user_id=1, guild_id=2,
                model=None
            ))
        self.assertEqual(out, "ok")

    def test_02_policy_empty_dict_with_explicit_model(self):
        """policy={} で model は引数側指定（None ではなく空辞書ルート）"""
        async def fake_ok(context_list, api_key, model=None, **extra):
            return f"ok:{model}"
        with patch("common.chat.chat_loop._extract_chat_policy_from_sessions",
                   return_value={} ), \
             patch("common.chat.chat_loop._resolve_api_key",
                   return_value="KEY"), \
             patch("common.chat.chat_loop._get_provider_chat_fn",
                   return_value=fake_ok):
            out = asyncio.run(chat_run(
                provider="openai",
                context_list=["ping"],
                user_id=1, guild_id=2,
                model="explicit"
            ))
        self.assertEqual(out, "ok:explicit")

    def test_03_provider_returns_none_is_handled(self):
        """プロバイダ関数が None を返す → ハンドリング（既定のエラーメッセージ）"""
        async def fake_none(*args, **kwargs):
            return None
        with patch("common.chat.chat_loop._extract_chat_policy_from_sessions",
                   return_value={"model":"m"}), \
             patch("common.chat.chat_loop._resolve_api_key",
                   return_value="KEY"), \
             patch("common.chat.chat_loop._get_provider_chat_fn",
                   return_value=fake_none):
            out = asyncio.run(chat_run(
                provider="openai",
                context_list=["pong"],
                user_id=1, guild_id=2,
                model=None
            ))
        self.assertEqual(out, MSG_PROVIDER_ERROR)

if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ChatLoopCoverRestTest)
    mapping = {
        "test_01_provider_trim_and_upper_is_valid":      ("T05-04-01", "provider trim/upper is valid"),
        "test_02_policy_empty_dict_with_explicit_model": ("T05-04-02", "policy {} + explicit model"),
        "test_03_provider_returns_none_is_handled":      ("T05-04-03", "provider returns None -> handled"),
    }
    run_unittest_suite("T05-04", suite, mapping)
