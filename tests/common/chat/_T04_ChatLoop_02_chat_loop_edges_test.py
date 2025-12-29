# tests/T04_ChatLoop_02_chat_loop_edges_test.py
# ------------------------------------------------------------
# T04-02 : ChatLoop edges
# 目的:
#  - 明示 model が policy より優先されること
#  - policy の追加パラメータ(temperature 等)がプロバイダ関数に透過されること
#  - 例外発生時に既定メッセージ "（チャット実行でエラーが発生しました）" を返すこと
# 実装依存はモックで吸収（USM/SSM/SecretStore/プロバイダ呼び出し）
# 実行: python -m tests.T04_ChatLoop_02_chat_loop_edges_test
# ------------------------------------------------------------
import asyncio
import unittest
from unittest.mock import patch
from tests._report import run_unittest_suite

from common.chat.chat_loop import run as chat_run

class ChatLoopEdgesTest(unittest.TestCase):
    def test_01_explicit_model_overrides_policy(self):
        """明示 model が policy の model を上書き"""
        called = {}
        async def fake_call(context_list, api_key, model=None, **extra):
            # 明示 model を使っているかを検証
            called['model'] = model
            return "ok"
        with patch("common.chat.chat_loop._extract_chat_policy_from_sessions",
                   return_value={"model":"from-policy"}), \
             patch("common.chat.chat_loop._resolve_api_key",
                   return_value="KEY"), \
             patch("common.chat.chat_loop._get_provider_chat_fn",
                   return_value=fake_call):
            out = asyncio.run(chat_run(
                provider="openai",
                context_list=["ping"],
                user_id=1, guild_id=2,
                model="explicit-model"
            ))
        self.assertEqual(out, "ok")
        self.assertEqual(called.get('model'), "explicit-model")

    def test_02_extra_params_passthrough(self):
        """policy の追加パラメータが透過される（extra dict 内）"""
        seen = {}
        async def fake_call(context_list, api_key, model=None, **extra):
            seen['temperature'] = extra.get('temperature')
            seen['top_p'] = extra.get('top_p')
            return "ok"
        with patch("common.chat.chat_loop._extract_chat_policy_from_sessions",
                   return_value={"model":"m","temperature":0.3,"top_p":0.8}), \
             patch("common.chat.chat_loop._resolve_api_key",
                   return_value="KEY"), \
             patch("common.chat.chat_loop._get_provider_chat_fn",
                   return_value=fake_call):
            out = asyncio.run(chat_run(
                provider="openai",
                context_list=["hello"],
                user_id=1, guild_id=2,
                model=None
            ))
        self.assertEqual(out, "ok")
        self.assertEqual(seen.get('temperature'), 0.3)
        self.assertEqual(seen.get('top_p'), 0.8)

    def test_03_provider_fn_raises_is_handled(self):
        """プロバイダ関数例外 → 既定のエラーメッセージを返す"""
        async def boom(*args, **kwargs):
            raise RuntimeError("boom")
        with patch("common.chat.chat_loop._extract_chat_policy_from_sessions",
                   return_value={"model":"m"}), \
             patch("common.chat.chat_loop._resolve_api_key",
                   return_value="KEY"), \
             patch("common.chat.chat_loop._get_provider_chat_fn",
                   return_value=boom):
            out = asyncio.run(chat_run(
                provider="openai",
                context_list=["hello"],
                user_id=1, guild_id=2,
                model=None
            ))
        self.assertEqual(out, "（チャット実行でエラーが発生しました）")

if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ChatLoopEdgesTest)
    mapping = {
        "test_01_explicit_model_overrides_policy": ("COMMON-CHAT:T04-02-01", "explicit model overrides policy"),
        "test_02_extra_params_passthrough":        ("COMMON-CHAT:T04-02-02", "extra params passthrough"),
        "test_03_provider_fn_raises_is_handled":   ("COMMON-CHAT:T04-02-03", "provider fn raises -> handled"),
    }
    run_unittest_suite("COMMON-CHAT:T04-02 common/chat/chat_loop", suite, mapping)
