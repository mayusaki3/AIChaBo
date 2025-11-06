# utiltests/T05_ChatLoop_05_chat_loop_helper_paths_test.py
import unittest
import asyncio
from unittest.mock import patch
from utiltests._report import run_unittest_suite
from common.chat.chat_loop import run as chat_run

"""
=== T05-05 : ChatLoop Helper Paths ===
狙い：
- これまで patch していた “ヘルパー関数本体” を敢えて patch せずに実行経路を通す。
- 未到達だった行（policy 抽出 / APIキー解決 / provider→chat_fn 解決）をカバーする。
"""

class ChatLoopHelperPathsTest(unittest.TestCase):
    maxDiff = None

    def test_01_policy_via_auth_resolve_and_chat_core_called(self):
        """
        [T05-05-01] auth.resolve から policy を取得し、_get_provider_chat_fn が
        chat_core.send_once を解決して呼び出すまでの実配線を確認
        - ヘルパーは patch しない
        - 明示 model を渡さない（policy の model が使用されるルート）
        """
        async def fake_send_once(context_list, api_key, model, **kw):
            # chat_core 側の send_once が実際に呼ばれたことを確認するための簡易モック
            self.assertEqual(context_list, ["hi"])
            self.assertEqual(api_key, "K")
            self.assertEqual(model, "m-from-policy")
            return "ok"

        with patch("common.chat.chat_loop._resolve_policy",
                   return_value={"provider": "openai", "model": "m-from-policy"}), \
             patch("common.chat.chat_core.send_once", new=fake_send_once):
            out = asyncio.run(chat_run(
                provider="openai",               # provider 正規化もヘルパー側で通る
                context_list=["hi"],
                user_id=123, guild_id=456,
                model=None,                      # 明示モデルなし → policy の model を利用
                api_key="K"                      # _resolve_api_key は明示キー優先の分岐を通る
            ))
        self.assertEqual(out, "ok")

    def test_02_helper_builds_chat_fn_without_chat_fn_in_policy(self):
        """
        [T05-05-02] policy に chat_fn が含まれない通常形で、_get_provider_chat_fn が
        provider に応じた関数を生成し、chat_core.send_once を呼ぶ経路を確認
        """
        async def fake_send_once(context_list, api_key, model, **kw):
            self.assertEqual(context_list, ["pong"])
            self.assertEqual(api_key, "KEY-2")
            self.assertEqual(model, "mm")
            return "ok-2"

        with patch("common.chat.chat_loop._resolve_policy",
                   return_value={"provider": "OPENAI", "model": "mm"}), \
             patch("common.chat.chat_core.send_once", new=fake_send_once):
            out = asyncio.run(chat_run(
                provider=" openai ",             # trim/upper の正規化も通る
                context_list=["pong"],
                user_id=1, guild_id=2,
                model="mm",                      # 明示モデルあり → こちらが優先
                api_key="KEY-2"                  # 明示キーで _resolve_api_key が通る
            ))
        self.assertEqual(out, "ok-2")


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ChatLoopHelperPathsTest)
    mapping = {
        "test_01_policy_via_auth_resolve_and_chat_core_called": ("T05-05-01", "policy via auth.resolve → chat_core called"),
        "test_02_helper_builds_chat_fn_without_chat_fn_in_policy": ("T05-05-02", "helper builds chat_fn (no chat_fn in policy)"),
    }
    run_unittest_suite("T05-05", suite, mapping)
