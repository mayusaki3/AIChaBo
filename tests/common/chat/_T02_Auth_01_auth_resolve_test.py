# -*- coding: utf-8 -*-
"""
T02_Auth_01_auth_resolve_test.py
目的: resolve_auth_and_key() の主要分岐を網羅テスト（opt-in）
実行例:
  # bash/zsh
  export AIChaBo_TEST_ENABLE_AUTH_RESOLVE=1
  python -m tests.T02_Auth_01_auth_resolve_test
  unset AIChaBo_TEST_ENABLE_AUTH_RESOLVE

  # PowerShell
  $env:AIChaBo_TEST_ENABLE_AUTH_RESOLVE=1
  python -m tests.T02_Auth_01_auth_resolve_test
  Remove-Item Env:AIChaBo_TEST_ENABLE_AUTH_RESOLVE
"""
import os
import unittest
from typing import Dict, Any

# 対象関数と、その内部で参照する USM/SSM/store を直接モンキーパッチする
from common.chat import auth as AUTH_MOD
from tests._report import run_unittest_suite

resolve_auth_and_key = AUTH_MOD.resolve_auth_and_key

def _mk_usm(chat: Dict[str, Any]):
    class _USM:
        @staticmethod
        def get_session(user_id):
            return {"chat": chat} if user_id else None
    return _USM

def _mk_ssm(chat: Dict[str, Any]):
    class _SSM:
        @staticmethod
        def get_shared_auth_config(guild_id):
            return {"chat": chat} if guild_id else None
    return _SSM

def _mk_store(user_key: bytes | None = None, server_keys: Dict[str, bytes] | None = None):
    class _STORE:
        @staticmethod
        def get_user_key(uid, prov):
            return user_key

        @staticmethod
        def get_server_keys(gid):
            return server_keys or {}
    return _STORE

@unittest.skipUnless(os.environ.get("AIChaBo_TEST_ENABLE_AUTH_RESOLVE") == "1",
                     "set AIChaBo_TEST_ENABLE_AUTH_RESOLVE=1 to run")
class AuthResolveTest(unittest.TestCase):
    def setUp(self):
        # 元モジュール参照を退避
        self._USM = AUTH_MOD.USM
        self._SSM = AUTH_MOD.SSM
        self._STORE = AUTH_MOD.store

    def tearDown(self):
        # 元に戻す
        AUTH_MOD.USM = self._USM
        AUTH_MOD.SSM = self._SSM
        AUTH_MOD.store = self._STORE

    # [T02-01-01] 未登録時は {} を返す（ベースライン）
    def test_01_resolve_without_any_auth(self):
        AUTH_MOD.USM = _mk_usm(chat={})
        AUTH_MOD.SSM = _mk_ssm(chat={})
        AUTH_MOD.store = _mk_store(user_key=None, server_keys=None)
        got = resolve_auth_and_key(user_id=123, guild_id=456)
        self.assertEqual(got, {})

    # [T02-01-02] USMにprovider/modelはあるがAPIキー未登録 -> {}
    def test_02_usm_config_no_keys(self):
        AUTH_MOD.USM = _mk_usm(chat={"provider": "OpenAI", "model": "gpt-4o-mini"})
        AUTH_MOD.SSM = _mk_ssm(chat={})
        AUTH_MOD.store = _mk_store(user_key=None, server_keys=None)
        got = resolve_auth_and_key(user_id=111, guild_id=222)
        self.assertEqual(got, {})

    # [T02-01-03] ユーザーキー優先で解決（max_tokens デフォルト付与）
    def test_03_resolve_with_user_key(self):
        AUTH_MOD.USM = _mk_usm(chat={"provider": "OpenAI", "model": "gpt-4o-mini"})
        AUTH_MOD.SSM = _mk_ssm(chat={})
        AUTH_MOD.store = _mk_store(user_key=b"USERKEY", server_keys=None)
        got = resolve_auth_and_key(user_id=1, guild_id=2)
        self.assertEqual(got.get("provider"), "openai")   # normalize_provider 済みを返す仕様
        self.assertEqual(got.get("model"), "gpt-4o-mini")
        self.assertEqual(got.get("api_key"), "USERKEY")
        self.assertEqual(got.get("max_tokens"), 2048)     # 既定値

    # [T02-01-04] ユーザーにキー無し・サーバーにあり → サーバーキーで解決
    def test_04_resolve_with_server_key_fallback(self):
        AUTH_MOD.USM = _mk_usm(chat={"provider": "OpenAI", "model": "gpt-4o-mini"})
        AUTH_MOD.SSM = _mk_ssm(chat={"provider": "IGNORED", "model": "IGNORED"})
        AUTH_MOD.store = _mk_store(user_key=None, server_keys={"openai": b"SVRKEY"})
        got = resolve_auth_and_key(user_id=10, guild_id=20)
        self.assertEqual(got.get("provider"), "openai")
        self.assertEqual(got.get("api_key"), "SVRKEY")

    # [T02-01-05] provider は大文字/別表記でも normalize → SecretStore の小文字キーに一致
    def test_05_provider_normalize_to_secretstore_key(self):
        AUTH_MOD.USM = _mk_usm(chat={"provider": "OPENAI", "model": "gpt-4o-mini"})
        AUTH_MOD.SSM = _mk_ssm(chat={})
        AUTH_MOD.store = _mk_store(user_key=b"X", server_keys=None)  # prov='openai' を期待
        got = resolve_auth_and_key(user_id=7, guild_id=8)
        self.assertEqual(got.get("provider"), "openai")
        self.assertEqual(got.get("api_key"), "X")

    # [T02-01-06] model 欠落 → {}
    def test_06_missing_model(self):
        AUTH_MOD.USM = _mk_usm(chat={"provider": "OpenAI"})
        AUTH_MOD.SSM = _mk_ssm(chat={})
        AUTH_MOD.store = _mk_store(user_key=b"K", server_keys=None)
        got = resolve_auth_and_key(user_id=1, guild_id=2)
        self.assertEqual(got, {})

    # [T02-01-07] USM になければ SSM の非機密を採用して解決
    def test_07_ssm_used_when_usm_absent(self):
        AUTH_MOD.USM = _mk_usm(chat={})  # 実質なし
        AUTH_MOD.SSM = _mk_ssm(chat={"provider": "OpenAI", "model": "gpt-4o-mini"})
        AUTH_MOD.store = _mk_store(user_key=None, server_keys={"openai": b"SVR"})
        got = resolve_auth_and_key(user_id=None, guild_id=999)  # user_id なしで SSM 経路を強制
        self.assertEqual(got.get("provider"), "openai")
        self.assertEqual(got.get("api_key"), "SVR")

if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(AuthResolveTest)
    # 正式番号: M02（common/chat） > T02-01（Auth）
    mapping = {
        "test_01_resolve_without_any_auth": ("COMMON-CHAT:T02-01-01", "resolve without any auth"),
        "test_02_usm_config_no_keys":      ("COMMON-CHAT:T02-01-02", "USM provider/model but no keys -> {}"),
        "test_03_resolve_with_user_key":   ("COMMON-CHAT:T02-01-03", "user key preferred"),
        "test_04_resolve_with_server_key_fallback": ("COMMON-CHAT:T02-01-04", "fallback to server key"),
        "test_05_provider_normalize_to_secretstore_key": ("COMMON-CHAT:T02-01-05", "provider normalize -> secretstore key"),
        "test_06_missing_model":           ("COMMON-CHAT:T02-01-06", "missing model -> {}"),
        "test_07_ssm_used_when_usm_absent":("COMMON-CHAT:T02-01-07", "use SSM when USM absent"),
    }
    run_unittest_suite("COMMON-CHAT:T02-01 common/chat/auth", suite, mapping)
