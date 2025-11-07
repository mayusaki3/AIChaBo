# -*- coding: utf-8 -*-
"""
T05-07 : ChatLoop helper functions

対象:
  - common.chat.chat_loop._extract_chat_policy_from_sessions
  - common.chat.chat_loop._resolve_api_key
  - common.chat.chat_loop._get_provider_chat_fn

目的:
  - T05-01〜06 でモックしていた内部ヘルパの分岐ロジックを直接テストし、chat_loop.py のカバレッジを向上させる。
  - 外部依存（USM/SSM/SecretStore/ai.*）は unittest.mock により差し替え、安全なユニットテストとする。

前提(実装準拠):
  - _extract_chat_policy_from_sessions(user_id, guild_id)
      USM/SSM の get_all_non_secret_policy を用い、
      server_policy をベースに user_policy で上書き（ユーザー優先）して dict を返す。
  - _resolve_api_key(user_id, guild_id, provider)
      store.get_user_key(user_id, provider) → store.get_server_key(guild_id, provider) の順で探索。
      見つからなければ None。
  - _get_provider_chat_fn(provider)
      importlib.import_module(f"ai.{provider}.{provider}_api") を行い、
      call_{provider}_chat を取得して返す。無ければ RuntimeError。
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

        # chat_loop モジュール内で参照される USM/SSM を差し替え
        with patch.object(chat_loop, "SSM", fake_ssm), \
             patch.object(chat_loop, "USM", fake_usm):
            policy = chat_loop._extract_chat_policy_from_sessions(user_id=1, guild_id=2)

        self.assertEqual(policy.get("model"), "user-model")  # user が上書き
        self.assertEqual(policy.get("top_p"), 0.9)           # server の値を保持
        self.assertEqual(policy.get("temp"), 0.2)            # user のみの値を反映

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

        # case-2: user 無し → server
        store_mock = MagicMock()
        store_mock.get_user_key.return_value = None
        store_mock.get_server_key.return_value = "SERVER_KEY"

        with patch.object(chat_loop, "store", store_mock):
            key = chat_loop._resolve_api_key(user_id=1, guild_id=2, provider="openai")
            self.assertEqual(key, "SERVER_KEY")

        # case-3: どちらも無し → None
        store_mock = MagicMock()
        store_mock.get_user_key.return_value = None
        store_mock.get_server_key.return_value = None

        with patch.object(chat_loop, "store", store_mock):
            key = chat_loop._resolve_api_key(user_id=1, guild_id=2, provider="openai")
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
    }

    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ChatLoopHelpersTest)
    run_unittest_suite("T05-07", suite, mapping)
