# tests/T05_ChatLoop_05_chat_loop_helper_paths_test.py
import unittest
import asyncio
from unittest.mock import patch
from tests._report import run_unittest_suite
from common.chat.chat_loop import run as chat_run

"""
=== T05-05 : ChatLoop Helper Paths ===
狙い（実装に追従）:
- chat_loop 側の “ヘルパー実装” 名称に合わせて patch 対象を更新
  * _extract_chat_policy_from_sessions : セッションから policy を集約
  * _resolve_api_key                  : ユーザー→サーバーの順でAPIキー解決
  * _get_provider_chat_fn             : provider から実際のチャット関数を解決
- ヘルパー間の配線（policy選択 → APIキー解決 → provider関数呼び出し）を素直に通す
- 実在しない ai.* モジュールには触れないよう、_get_provider_chat_fn だけはテスト内で差し替え
"""

class ChatLoopHelperPathsTest(unittest.TestCase):
    maxDiff = None

    def test_01_policy_via_sessions_and_chat_core_called(self):
        """
        [T05-05-01] セッション由来の policy（model=m-from-policy）を用い、
        _resolve_api_key が呼ばれ(K)を返し、_get_provider_chat_fn が返す関数経由で
        実行できることを確認。model は「明示指定なし→policyのmodel」を使うルート。
        """
        async def fake_provider_chat(context_list, api_key, model, **kw):
            # 経路・値の検証
            self.assertEqual(context_list, ["hi"])
            self.assertEqual(api_key, "K")
            self.assertEqual(model, "m-from-policy")
            # policy の余剰パラメータ（provider/model以外）が extra として渡ることも確認可能
            self.assertEqual(kw.get("temperature"), 0.3)
            return "ok"

        with patch("common.chat.chat_loop._extract_chat_policy_from_sessions",
                   return_value={"provider": "openai", "model": "m-from-policy", "temperature": 0.3}), \
             patch("common.chat.chat_loop._resolve_api_key", return_value="K"), \
             patch("common.chat.chat_loop._get_provider_chat_fn", return_value=fake_provider_chat):
            out = asyncio.run(chat_run(
                provider="openai",
                context_list=["hi"],
                user_id=123, guild_id=456,
                model=None  # 明示モデルなし → policy の model を利用
            ))
        self.assertEqual(out, "ok")

    def test_02_helper_builds_chat_fn_with_explicit_model_override(self):
        """
        [T05-05-02] 明示 model が policy の model を上書きする経路。
        provider の正規化や extra パラメータの受け渡しも通ることを確認。
        """
        async def fake_provider_chat(context_list, api_key, model, **kw):
            self.assertEqual(context_list, ["pong"])
            self.assertEqual(api_key, "KEY-2")
            # 明示 model が policy の model を上書きする想定
            self.assertEqual(model, "mm-explicit")
            # policy 側の余剰パラメータが extra として渡る
            self.assertEqual(kw.get("top_p"), 0.7)
            return "ok-2"

        with patch("common.chat.chat_loop._extract_chat_policy_from_sessions",
                   return_value={"provider": "OPENAI", "model": "mm-policy", "top_p": 0.7}), \
             patch("common.chat.chat_loop._resolve_api_key", return_value="KEY-2"), \
             patch("common.chat.chat_loop._get_provider_chat_fn", return_value=fake_provider_chat):
            out = asyncio.run(chat_run(
                provider=" openai ",   # trim/upper 正規化も chat_loop 内で通る
                context_list=["pong"],
                user_id=1, guild_id=2,
                model="mm-explicit"    # 明示モデル優先
            ))
        self.assertEqual(out, "ok-2")


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ChatLoopHelperPathsTest)
    mapping = {
        "test_01_policy_via_sessions_and_chat_core_called": ("T05-05-01", "policy via sessions → provider chat called"),
        "test_02_helper_builds_chat_fn_with_explicit_model_override": ("T05-05-02", "explicit model overrides policy; extra passthrough"),
    }
    run_unittest_suite("T05-05", suite, mapping)
