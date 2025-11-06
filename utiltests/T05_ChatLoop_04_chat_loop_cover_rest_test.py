# T05-04 : ChatLoop cover rest branches
# 狙い: chat_loop.py の未到達(14–27, 34–43, 51–59, 101)をコード変更なしでテスト到達
# 実行: python -m utiltests.T05_ChatLoop_04_chat_loop_cover_rest_test

import asyncio
import unittest
from unittest.mock import patch
from utiltests._report import run_unittest_suite

# 被テスト対象
from common.chat.chat_loop import run as chat_run

# 既定エラーメッセージ（chat_loop 側のフォールバックと整合させる）
MSG_PROVIDER_ERROR = "（チャット実行でエラーが発生しました）"


class ChatLoopCoverRestTest(unittest.TestCase):
    def test_01_provider_trim_and_upper_is_valid(self):
        """
        [T05-04-01] provider 前処理の枝:
        '  OPENAI  '（前後空白 + 大文字）でも有効として処理されることを確認。
        - policy は model を持つ正常ケース
        - APIキーは存在
        - provider関数は正常応答を返す
        期待: "ok"
        """
        async def fake_ok(context_list, api_key, model=None, **extra):
            # provider 正規化後に到達できればOK
            return "ok"

        with patch("common.chat.chat_loop._extract_chat_policy_from_sessions",
                   return_value={"model": "m"}), \
             patch("common.chat.chat_loop._resolve_api_key",
                   return_value="KEY"), \
             patch("common.chat.chat_loop._get_provider_chat_fn",
                   return_value=fake_ok):
            out = asyncio.run(chat_run(
                provider="  OPENAI  ",           # ← 前処理で正規化されるべき入力
                context_list=["hello"],
                user_id=1, guild_id=2,
                model=None                      # policy側の model を使う
            ))
        self.assertEqual(out, "ok")

    def test_02_policy_empty_dict_with_explicit_model(self):
        """
        [T05-04-02] policy が空辞書 {} の枝:
        - policy=None は T05-03-03 で「既定エラーメッセージ」に落ちる仕様だが、
          policy={} は None とは別枝。model は引数側で明示指定し正常完了させる。
        期待: "ok:explicit"
        """
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
                model="explicit"                # ← 引数側で model 指定
            ))
        self.assertEqual(out, "ok:explicit")

    def test_03_provider_returns_none_is_stringified(self):
        """
        [T05-04-03] 戻り値後処理の枝（現行仕様）:
        - provider 関数が None を返すと、str(None) → "None" として返る仕様
        期待: "None"
        """
        async def fake_none(*args, **kwargs):
            return None

        with patch("common.chat.chat_loop._extract_chat_policy_from_sessions",
                   return_value={"model": "m"}), \
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
        self.assertEqual(out, "None")


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ChatLoopCoverRestTest)
    # レポータ表示用マッピング（順序固定: test_01 → test_02 → test_03）
    mapping = {
        "test_01_provider_trim_and_upper_is_valid":        ("T05-04-01", "provider trim/upper is valid"),
        "test_02_policy_empty_dict_with_explicit_model":   ("T05-04-02", "policy {} + explicit model"),
        "test_03_provider_returns_none_is_stringified":    ("T05-04-03", 'provider returns None -> "None" string'),
    }
    from utiltests._report import run_unittest_suite
    run_unittest_suite("T05-04", suite, mapping)
