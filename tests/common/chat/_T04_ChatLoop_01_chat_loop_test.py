# tests/T04_ChatLoop_01_chat_loop_test.py
# ------------------------------------------------------------
# T04-01 : ChatLoop 基本
# 対象: common/chat/chat_loop.py の async run()
# 目的:
#  - 空入力 → "（入力が空です）"
#  - model 未解決 → "（モデル設定が見つかりません。/ac_auth で設定してください）"
#  - 正常系（policy/model 補完 + api_key 解決 + プロバイダ関数呼出）
#  - provider 不正 → "（プロバイダが不正です）"
# 依存:
#  - USM/SSM/SecretStore/AI 実体には依存させず、内部ヘルパを patch して検証
# 実行:
#  - python -m tests.T04_ChatLoop_01_chat_loop_test
# 出力:
#  - ✅/❌ [T04-01-xx] ... と --- SUMMARY T04-01: ... --- を共通レポータで統一
# ------------------------------------------------------------
import asyncio
import unittest
from unittest.mock import patch
from tests._report import run_unittest_suite

# テスト対象: async run()
from common.chat.chat_loop import run as chat_run

class ChatLoopBasicTest(unittest.TestCase):
    """
    ケース設計
      T04-01-01: 空入力 → 固定文言
      T04-01-02: model 未解決（引数 None & policy も空）→ ガイダンス
      T04-01-03: 正常系（policy で model 補完、api_key 解決、AI呼出→応答文字列）
      T04-01-04: provider 不正（空/空白）→ 固定文言
    """

    def test_01_empty_input_returns_fixed_message(self):
        """空入力 → "（入力が空です）" を返す"""
        # context_list が空/空白のみだと "（入力が空です）"
        res = asyncio.run(chat_run(
            provider="openai",
            context_list=["   "],
            user_id=1, guild_id=2,
            model="gpt-4o-mini"  # model があっても入力空なら先に弾かれる
        ))
        self.assertEqual(res, "（入力が空です）")

    def test_02_missing_model_message(self):
        """model 未解決（引数 None & policy も空）→ ガイダンス文言"""
        # policy が空（model 補完なし）・引数 model=None → ガイダンス
        with patch("common.chat.chat_loop._extract_chat_policy_from_sessions", return_value={}):
            res = asyncio.run(chat_run(
                provider="openai",
                context_list=["hello"],
                user_id=1, guild_id=2,
                model=None
            ))
        self.assertIn("モデル設定が見つかりません", res)

    def test_03_happy_path_with_patched_env(self):
        """正常系（policy で model 補完、api_key 解決、AI呼出→応答文字列）"""
        async def fake_call(context_list, api_key, model=None, **extra):
            # chat_fn の代替: 期待通りの引数が来ることも確認
            assert isinstance(context_list, list) and context_list and isinstance(context_list[0], str)
            assert api_key == "KEY"
            assert model == "m"
            return "pong"

        with patch("common.chat.chat_loop._extract_chat_policy_from_sessions", return_value={"model": "m"}), \
             patch("common.chat.chat_loop._resolve_api_key", return_value="KEY"), \
             patch("common.chat.chat_loop._get_provider_chat_fn", return_value=fake_call):
            res = asyncio.run(chat_run(
                provider="openai",
                context_list=["ping"],
                user_id=10, guild_id=20,
                model=None  # policy 補完を使う
            ))
        self.assertEqual(res, "pong")

    def test_04_invalid_provider_message(self):
        """provider 不正（空/空白）→ 固定文言"""
        res = asyncio.run(chat_run(
            provider="   ",
            context_list=["hello"],
            user_id=1, guild_id=2,
            model="gpt"
        ))
        self.assertEqual(res, "（プロバイダが不正です）")


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ChatLoopBasicTest)
    mapping = {
        "test_01_empty_input_returns_fixed_message": ("COMMON-CHAT:T04-01-01", "empty -> fixed message"),
        "test_02_missing_model_message":             ("COMMON-CHAT:T04-01-02", "missing model -> guidance"),
        "test_03_happy_path_with_patched_env":       ("COMMON-CHAT:T04-01-03", "happy path (patched)"),
        "test_04_invalid_provider_message":          ("COMMON-CHAT:T04-01-04", "invalid provider -> message"),
    }
    run_unittest_suite("COMMON-CHAT:T04-01 common/chat/chat_loop", suite, mapping)
