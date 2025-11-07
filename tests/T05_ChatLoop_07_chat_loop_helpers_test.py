# -*- coding: utf-8 -*-
"""
T05-07 : ChatLoop helper functions

対象:
  - common.chat.chat_loop._extract_chat_policy_from_sessions
  - common.chat.chat_loop._resolve_api_key
  - common.chat.chat_loop._get_provider_chat_fn

目的:
  - T05-01〜06でモックしていた内部ヘルパの分岐ロジックを直接テストし、chat_loop.py のカバレッジを 100% に近づける。
  - 外部依存（USM/SSM/SecretStore/ai.*）は unittest.mock により差し替え、安全なユニットテストとする。
"""

import types
import unittest
from unittest.mock import patch, MagicMock

from tests._report import run_unittest_suite
from common.chat import chat_loop


class ChatLoopHelpersTest(unittest.TestCase):
    """
    chat_loop 内部ヘルパ3関数の分岐仕様テスト。
    """

    # [T05-07-01]
    # _extract_chat_policy_from_sessions:
    #  - guild 側と user 側の non-secret policy を統合
    #  - 衝突時は user 側で server 側を上書き（ユーザー優先）
    def test_01_extract_policy_user_overrides_server(self):
        fake_ssm = types.SimpleNamespace(
            get_all_non_secret_policy=lambda gid: {"model": "server-model", "top_p": 0.9}
        )
        fake_usm = types.SimpleNamespace(
            get_all_non_secret_policy=lambda uid: {"model": "user-model", "temp": 0.2}
        )

        with patch.object(chat_loop, "SSM", fake_ssm), \
             patch.object(chat_loop, "USM", fake_usm):
            policy = chat_loop._extract_chat_policy_from_sessions(user_id=1, guild_id=2)

        # user が model を上書き
        self.assertEqual(policy.get("model"), "user-model")
        # server の項目も保持
        self.assertEqual(policy.get("top_p"), 0.9)
        # user の追加項目も反映
        self.assertEqual(policy.get("temp"), 0.2)

    # [T05-07-02]
    # _resolve_api_key:
    #  - user キー優先 → 無ければ server キー → 無ければ None
    def test_02_resolve_api_key_priority_user_then_server_then_none(self):
        # case-1: user key 優先
        store_mock = MagicMock()
        store_mock.get_user_key.return_value = "USER_KEY"
        store_mock.get_server_key.return_value = "SERVER_KEY"

        with patch.object(chat_loop, "store", store_mock):
            key = chat_loop._resolve_api_key(user_id=1, guild_id=2, provider="openai")
            self.assertEqual(key, "USER_KEY")

        # case-2: user 無し → server（user_id=None パスも通す）
        store_mock = MagicMock()
        store_mock.get_user_key.return_value = None
        store_mock.get_server_key.return_value = "SERVER_KEY"

        # user_id は None: user 分岐をスキップして server 分岐のみ通る
        with patch.object(chat_loop, "store", store_mock):
            key = chat_loop._resolve_api_key(user_id=None, guild_id=2, provider="openai")
            self.assertEqual(key, "SERVER_KEY")

        # case-3: どちらも無し → None（両方 None パスを通す）
        store_mock = MagicMock()
        store_mock.get_user_key.return_value = None
        store_mock.get_server_key.return_value = None

        with patch.object(chat_loop, "store", store_mock):
            key = chat_loop._resolve_api_key(user_id=None, guild_id=None, provider="openai")
            self.assertIsNone(key)

    # [T05-07-03]
    # _get_provider_chat_fn:
    #  - ai.{provider}.{provider}_api から call_{provider}_chat を取得できること
    def test_03_get_provider_chat_fn_success(self):
        provider = "dummy"
        fake_mod = types.SimpleNamespace()

        def fake_chat(*args, **kwargs):
            return "ok"

        setattr(fake_mod, f"call_{provider}_chat", fake_chat)

        # chat_loop.py は importlib を直接 import しているため、
        # patch 対象は "importlib.import_module"
        with patch("importlib.import_module", return_value=fake_mod):
            fn = chat_loop._get_provider_chat_fn(provider)

        self.assertIs(fn, fake_chat)

    # [T05-07-04]
    # _get_provider_chat_fn:
    #  - エントリポイント欠如時に RuntimeError を送出すること
    def test_04_get_provider_chat_fn_missing_raises_runtime_error(self):
        provider = "ghost"
        fake_mod = types.SimpleNamespace()  # call_ghost_chat を持たない

        with patch("importlib.import_module", return_value=fake_mod):
            with self.assertRaises(RuntimeError):
                chat_loop._get_provider_chat_fn(provider)

    # [T05-07-05]
    # _extract_chat_policy_from_sessions:
    #  - guild_id のみ指定された場合は SSM のみ参照し、その結果を返す
    def test_05_extract_policy_guild_only(self):
        fake_ssm = types.SimpleNamespace(
            get_all_non_secret_policy=lambda gid: {"model": "server-model"}
        )
        fake_usm = MagicMock()

        with patch.object(chat_loop, "SSM", fake_ssm), \
             patch.object(chat_loop, "USM", fake_usm):
            policy = chat_loop._extract_chat_policy_from_sessions(user_id=None, guild_id=2)

        self.assertEqual(policy, {"model": "server-model"})
        fake_usm.get_all_non_secret_policy.assert_not_called()

    # [T05-07-06]
    # _extract_chat_policy_from_sessions:
    #  - user_id/guild_id ともに None の場合、USM/SSM を呼ばず {} を返す
    def test_06_extract_policy_none_ids_returns_empty(self):
        fake_ssm = MagicMock()
        fake_usm = MagicMock()

        with patch.object(chat_loop, "SSM", fake_ssm), \
             patch.object(chat_loop, "USM", fake_usm):
            policy = chat_loop._extract_chat_policy_from_sessions(user_id=None, guild_id=None)

        self.assertEqual(policy, {})
        fake_ssm.get_all_non_secret_policy.assert_not_called()
        fake_usm.get_all_non_secret_policy.assert_not_called()


if __name__ == "__main__":
    mapping = {
        "test_01_extract_policy_user_overrides_server":
            ("T05-07-01", "_extract_chat_policy_from_sessions: user overrides server"),
        "test_02_resolve_api_key_priority_user_then_server_then_none":
            ("T05-07-02", "_resolve_api_key: user > server > None"),
        "test_03_get_provider_chat_fn_success":
            ("T05-07-03", "_get_provider_chat_fn: uses ai.{provider}.{provider}_api.call_{provider}_chat"),
        "test_04_get_provider_chat_fn_missing_raises_runtime_error":
            ("T05-07-04", "_get_provider_chat_fn: missing entry -> RuntimeError"),
        "test_05_extract_policy_guild_only":
            ("T05-07-05", "_extract_chat_policy_from_sessions: guildのみ指定 -> SSMのみ"),
        "test_06_extract_policy_none_ids_returns_empty":
            ("T05-07-06", "_extract_chat_policy_from_sessions: user/guild無し -> {} & USM/SSM未呼び出し"),
    }

    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ChatLoopHelpersTest)
    run_unittest_suite("T05-07", suite, mapping)
