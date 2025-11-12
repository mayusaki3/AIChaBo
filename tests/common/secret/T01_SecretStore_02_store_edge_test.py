import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from common.secret import store as store_mod
from tests._report import run_unittest_suite


class _TempStoreEnv:
    """
    SecretStore のストレージパスを一時ディレクトリに切り替えてテストするコンテキスト。

    - MASTER_KEY_PATH / USERS_JSON / SERVERS_JSON / store を退避して差し替え
    - 終了時に元に戻して一時ディレクトリを削除
    """

    def __enter__(self):
        self.root = Path(tempfile.mkdtemp(prefix="aichabo_M01T01_02_"))
        self.users = self.root / "users.json"
        self.servers = self.root / "servers.json"
        self.master = self.root / "master.key"

        # 退避
        self._old_users = store_mod.USERS_JSON
        self._old_servers = store_mod.SERVERS_JSON
        self._old_master = store_mod.MASTER_KEY_PATH
        self._old_store = store_mod.store
        self._old_env_key = os.environ.get("AC_MASTER_KEY")

        # 一時パスに差し替え
        store_mod.USERS_JSON = self.users
        store_mod.SERVERS_JSON = self.servers
        store_mod.MASTER_KEY_PATH = self.master
        os.environ.pop("AC_MASTER_KEY", None)

        # 新しい SecretStore シングルトン
        self.store = store_mod.SecretStore()
        store_mod.store = self.store
        return self

    def __exit__(self, exc_type, exc, tb):
        # 元に戻す
        store_mod.USERS_JSON = self._old_users
        store_mod.SERVERS_JSON = self._old_servers
        store_mod.MASTER_KEY_PATH = self._old_master
        store_mod.store = self._old_store

        if self._old_env_key is not None:
            os.environ["AC_MASTER_KEY"] = self._old_env_key
        else:
            os.environ.pop("AC_MASTER_KEY", None)

        shutil.rmtree(self.root, ignore_errors=True)


class SecretStoreEdgesRecoveryTest(unittest.TestCase):
    """
    M01:T01-02
    SecretStore の周辺仕様・後方互換・壊れファイル復旧パスを検証。
    """

    # M01:T01-02-01
    def test_01_put_user_empty_provider_raises(self):
        with _TempStoreEnv() as env:
            with self.assertRaises(ValueError):
                env.store.put_user_key(1, "", b"KEY")

    # M01:T01-02-02
    def test_02_put_server_empty_provider_raises(self):
        with _TempStoreEnv() as env:
            with self.assertRaises(ValueError):
                env.store.put_server_key(1, "", b"KEY")

    # M01:T01-02-03
    def test_03_get_user_empty_provider_returns_none(self):
        with _TempStoreEnv() as env:
            self.assertIsNone(env.store.get_user_key(1, ""))

    # M01:T01-02-04
    def test_04_get_server_empty_provider_returns_none(self):
        with _TempStoreEnv() as env:
            self.assertIsNone(env.store.get_server_key(1, ""))

    # M01:T01-02-05
    def test_05_has_server_any_key_false_then_true(self):
        with _TempStoreEnv() as env:
            ss = env.store
            gid = 10
            # 初期は False
            self.assertFalse(ss.has_server_any_key(gid))
            # 鍵を1つ追加すると True
            ss.put_server_key(gid, "openai", b"K")
            self.assertTrue(ss.has_server_any_key(gid))

    # M01:T01-02-06
    def test_06_delete_server_keys_safe_when_no_entry(self):
        with _TempStoreEnv() as env:
            ss = env.store
            gid = 20
            # 存在しなくても例外なく動く
            ss.delete_server_keys(gid)
            self.assertFalse(ss.has_server_any_key(gid))

    # M01:T01-02-07
    def test_07_backward_compat_no_prefix(self):
        """
        旧データ形式（"fernet:" プレフィックスなし）でも復号できることを確認。
        """
        with _TempStoreEnv() as env:
            ss = env.store
            # プレフィックス無しトークンを直接書き込む
            plain = b"OLD"
            raw_token = ss._fernet.encrypt(plain).decode("utf-8")  # _enc は使わず prefix 無し
            data = {
                "1": {
                    "providers": {
                        "openai": raw_token,
                    }
                }
            }
            env.users.write_text(json.dumps(data), encoding="utf-8")

            self.assertEqual(ss.get_user_key(1, "openai"), plain)

    # M01:T01-02-08
    def test_08_broken_json_is_recovered_to_empty(self):
        """
        壊れた JSON を読み込んだ場合:
        - _load_json は {} を返す
        - 復旧として空 JSON を書き戻す
        """
        with _TempStoreEnv() as env:
            ss = env.store

            # users.json を壊す
            env.users.write_text("{broken", encoding="utf-8")

            # 読み込み経由 API が例外を投げず None を返すこと
            self.assertIsNone(ss.get_user_key(1, "openai"))

            # 復旧後のファイルは正しい JSON（{}）になっていること
            loaded = json.loads(env.users.read_text(encoding="utf-8"))
            self.assertEqual(loaded, {})

    # M01:T01-02-09
    def test_09_delete_user_keys_clears_all(self):
        with _TempStoreEnv() as env:
            ss = env.store
            uid = 1
            ss.put_user_key(uid, "openai", b"A")
            ss.put_user_key(uid, "gemini", b"B")
            self.assertTrue(ss.get_user_keys(uid))

            ss.delete_user_keys(uid)
            self.assertEqual(ss.get_user_keys(uid), {})


# テスト番号マッピング（Reporter 用）
mapping = {
    "test_01_put_user_empty_provider_raises":
        ("M01:T01-02-01", "put_user: provider空 -> ValueError"),
    "test_02_put_server_empty_provider_raises":
        ("M01:T01-02-02", "put_server: provider空 -> ValueError"),
    "test_03_get_user_empty_provider_returns_none":
        ("M01:T01-02-03", "get_user: provider空 -> None"),
    "test_04_get_server_empty_provider_returns_none":
        ("M01:T01-02-04", "get_server: provider空 -> None"),
    "test_05_has_server_any_key_false_then_true":
        ("M01:T01-02-05", "has_server_any_key False/True"),
    "test_06_delete_server_keys_safe_when_no_entry":
        ("M01:T01-02-06", "delete_server_keys 安全"),
    "test_07_backward_compat_no_prefix":
        ("M01:T01-02-07", "旧prefixなし互換"),
    "test_08_broken_json_is_recovered_to_empty":
        ("M01:T01-02-08", "壊れJSON復旧"),
    "test_09_delete_user_keys_clears_all":
        ("M01:T01-02-09", "delete_user_keys 全削除"),
}


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(SecretStoreEdgesRecoveryTest)
    run_unittest_suite("M01:T01-02", suite, mapping)
