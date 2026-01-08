"""
tests.common.secret.T01_SecretStore_04_store_misc_test

[テストユーティリティ](../../README_TEST.md) > common/secretモジュール単体テスト
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tests._report import run_unittest_suite

from common.secret import store as store_mod


class SecretStoreMiscTest(unittest.TestCase):
    """
    COMMON-SECRET:T01-04 common/secret/store
    """

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)

        # store.py 側の保存先をテスト用に差し替え
        store_mod._BASE_DIR = self.base
        store_mod._USERS_PATH = self.base / "users.json"
        store_mod._SERVERS_PATH = self.base / "servers.json"
        store_mod._MASTER_KEY_PATH = self.base / "master.key"

        self.ss = store_mod.SecretStore()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_01_get_user_keys_partial_success(self) -> None:
        """
        [COMMON-SECRET:T01-04-01] get_user_keys 部分成功（破損トークンはスキップ）
        """
        # 正常な鍵を2つ入れる
        self.ss.put_user_key(user_id=1, provider="openai", key_bytes=b"sk-AAAA")
        self.ss.put_user_key(user_id=1, provider="gemini", key_bytes=b"AIzaBBBB")

        # 保存ファイルを直接破損させ、openai 側だけ復号不能にする（token文字列を破損させる）
        raw = json.loads(store_mod._USERS_PATH.read_text(encoding="utf-8"))
        # users.json の構造は { "<uid>": { "providers": { "<provider>": "<token str>" } } }
        raw["1"]["providers"]["openai"] = "BROKEN_TOKEN"
        store_mod._USERS_PATH.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")

        got = self.ss.get_user_keys(user_id=1)

        # 破損した openai は落ちずにスキップ、正常な gemini は取得できる
        self.assertNotIn("openai", got)
        self.assertIn("gemini", got)
        self.assertEqual(got["gemini"], b"AIzaBBBB")

    def test_02_get_server_keys_missing_gid_returns_empty(self) -> None:
        """
        [COMMON-SECRET:T01-04-02] get_server_keys gid無し->{}
        """
        self.assertEqual(self.ss.get_server_keys(guild_id=9999), {})

    def test_03_put_server_key_overwrite(self) -> None:
        """
        [COMMON-SECRET:T01-04-03] put_server_key 上書き
        """
        self.ss.put_server_key(guild_id=2, provider="openai", key_bytes=b"sk-OLD")
        self.ss.put_server_key(guild_id=2, provider="openai", key_bytes=b"sk-NEW")

        got = self.ss.get_server_key(guild_id=2, provider="openai")
        self.assertEqual(got, b"sk-NEW")

    def test_04_delete_empty_or_missing_is_safe_false(self) -> None:
        """
        [COMMON-SECRET:T01-04-04] delete_* 空/欠落でもFalse（堅牢性）
        """
        # 何も無い状態で delete → False（例外を出さない）
        self.assertFalse(self.ss.delete_user_keys(user_id=1, provider="openai"))
        self.assertFalse(self.ss.delete_server_keys(guild_id=2, provider="openai"))


def _suite() -> unittest.TestSuite:
    loader = unittest.TestLoader()
    return loader.loadTestsFromTestCase(SecretStoreMiscTest)


if __name__ == "__main__":
    suite = _suite()
    mapping = {
        "SecretStoreMiscTest.test_01_get_user_keys_partial_success": (
            "COMMON-SECRET:T01-04-01",
            "get_user_keys 部分成功（破損トークンはスキップ）",
        ),
        "SecretStoreMiscTest.test_02_get_server_keys_missing_gid_returns_empty": (
            "COMMON-SECRET:T01-04-02",
            "get_server_keys gid無し->{}",
        ),
        "SecretStoreMiscTest.test_03_put_server_key_overwrite": (
            "COMMON-SECRET:T01-04-03",
            "put_server_key 上書き",
        ),
        "SecretStoreMiscTest.test_04_delete_empty_or_missing_is_safe_false": (
            "COMMON-SECRET:T01-04-04",
            "delete_* 空/欠落でもFalse（堅牢性）",
        ),
    }
    run_unittest_suite("COMMON-SECRET:T01-04 common/secret/store", suite, mapping)
