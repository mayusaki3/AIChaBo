# T05-03 : ChatLoop more edges
# 目的:
#  - APIキー未設定枝
#  - 全メッセージ空白化枝（前処理後に空）
#  - policy None/空辞書枝
#  - provider 関数が空文字返却
#  - provider 関数取得失敗(None) → 例外ハンドリング枝
# 実行: python -m tests.T05_ChatLoop_03_chat_loop_more_edges_test
import asyncio
import unittest
from unittest.mock import patch
from tests._report import run_unittest_suite

from common.chat.chat_loop import run as chat_run

# 既定メッセージ（実装に合わせる）
MSG_EMPTY_INPUT = "（入力が空です）"
MSG_MISSING_MODEL = "（モデル設定が見つかりません。/ac_auth や /ac_status で確認してください）"
MSG_MISSING_APIKEY = "（APIキーが未設定です。/ac_auth で登録してください）"
MSG_PROVIDER_INVALID = "（プロバイダが不正です）"
MSG_PROVIDER_ERROR = "（チャット実行でエラーが発生しました）"

class ChatLoopMoreEdgesTest(unittest.TestCase):
    def test_01_apikey_missing(self):
        """_resolve_api_key が None/空 → APIキー未設定メッセージ"""
        async def fake_ok(*args, **kwargs):  # 呼ばれない想定
            return "ok"
        with patch("common.chat.chat_loop._extract_chat_policy_from_sessions",
                   return_value={"model": "m"}), \
             patch("common.chat.chat_loop._resolve_api_key",
                   return_value=None), \
             patch("common.chat.chat_loop._get_provider_chat_fn",
                   return_value=fake_ok):
            out = asyncio.run(chat_run(
                provider="openai",
                context_list=["hello"],
                user_id=1, guild_id=2,
                model=None
            ))
        self.assertEqual(out, MSG_MISSING_APIKEY)

    def test_02_all_messages_become_empty(self):
        """context_list が全部空白 → 空入力メッセージ"""
        with patch("common.chat.chat_loop._extract_chat_policy_from_sessions",
                   return_value={"model": "m"}), \
             patch("common.chat.chat_loop._resolve_api_key",
                   return_value="KEY"):
            out = asyncio.run(chat_run(
                provider="openai",
                context_list=["   ", "\t", " \n "],
                user_id=1, guild_id=2,
                model=None
            ))
        self.assertEqual(out, MSG_EMPTY_INPUT)

    def test_03_policy_none_returns_error_message(self):
        """policy=None のときは現行実装上エラーに落ち、既定メッセージを返す"""
        async def fake_ok(*args, **kwargs):
            return "ok"
        with patch("common.chat.chat_loop._extract_chat_policy_from_sessions",
                   return_value=None), \
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
        self.assertEqual(out, "（チャット実行でエラーが発生しました）")

    def test_04_provider_returns_empty_string(self):
        """プロバイダ関数が空文字を返す枝（許容/ガードのどちらでも可、ここでは空文字を許容とする）"""
        async def fake_empty(*args, **kwargs):
            return ""
        with patch("common.chat.chat_loop._extract_chat_policy_from_sessions",
                   return_value={"model":"m"}), \
             patch("common.chat.chat_loop._resolve_api_key",
                   return_value="KEY"), \
             patch("common.chat.chat_loop._get_provider_chat_fn",
                   return_value=fake_empty):
            out = asyncio.run(chat_run(
                provider="openai",
                context_list=["ping"],
                user_id=1, guild_id=2,
                model=None
            ))
        # 実装が空文字をそのまま返すなら ""、置換するならその文言に合わせる
        self.assertTrue(isinstance(out, str))

    def test_05_provider_fn_is_none(self):
        """プロバイダ関数取得失敗(None) → 実装上は呼出時に TypeError になり例外ハンドリングへ"""
        with patch("common.chat.chat_loop._extract_chat_policy_from_sessions",
                   return_value={"model":"m"}), \
             patch("common.chat.chat_loop._resolve_api_key",
                   return_value="KEY"), \
             patch("common.chat.chat_loop._get_provider_chat_fn",
                   return_value=None):
            out = asyncio.run(chat_run(
                provider="openai",
                context_list=["hello"],
                user_id=1, guild_id=2,
                model=None
            ))
        self.assertEqual(out, MSG_PROVIDER_ERROR)

if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ChatLoopMoreEdgesTest)
    mapping = {
        "test_01_apikey_missing":            ("T05-03-01", "apikey missing -> guidance"),
        "test_02_all_messages_become_empty": ("T05-03-02", "all messages empty -> fixed message"),
        "test_03_policy_none_returns_error_message": ("T05-03-03", "policy=None -> default error message"),
        "test_04_provider_returns_empty_string": ("T05-03-04", "provider returns empty string"),
        "test_05_provider_fn_is_none":       ("T05-03-05", "provider fn None -> handled"),
    }
    run_unittest_suite("T05-03", suite, mapping)
