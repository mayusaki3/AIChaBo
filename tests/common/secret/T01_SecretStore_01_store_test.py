# -*- coding: utf-8 -*-
"""
COMMON-SECRET:T01-01 SecretStore 基本動作 & 競合整合性テスト

目的:
  - ユーザ/サーバ鍵の put/get が往復で正しく動作する（永続化OK）
  - 複数スレッドの同時 put が発生しても provider 単位で LWW（Last-Write-Wins）
    となり、部分破損が起きない（混在が残らない）

実行例:
  python -m tests.common.secret.T01_SecretStore_01_store_test

出力:
  [COMMON-SECRET:T01-01-xx] ... 形式の行 + 共通SUMMARY（tests._report.run_unittest_suite）
"""

import os
import tempfile
import shutil
import threading
import unittest
from pathlib import Path

from tests._report import run_unittest_suite
import common.secret.store as store_mod


class _TempStoreEnv:
    """
    SecretStore が参照するパス（users.json / servers.json / master.key）を
    一時ディレクトリに差し替えるヘルパ。
    """

    def __init__(self) -> None:
        self._old_USERS = None
        self._old_SERVERS = None
        self._old_MKEY = None
        self._old_env_key = None
        self.root: Path | None = None
        self.users: Path | None = None
        self.servers: Path | None = None
        self.mkey: Path | None = None
        self.store: store_mod.SecretStore | None = None

    def __enter__(self):
        self.root = Path(tempfile.mkdtemp(prefix="aichabo_ss_M01T01_01_"))
        self.users = self.root / "users.json"
        self.servers = self.root / "servers.json"
        self.mkey = self.root / "master.key"

        # 定数退避
        self._old_USERS = store_mod.USERS_JSON
        self._old_SERVERS = store_mod.SERVERS_JSON
        self._old_MKEY = store_mod.MASTER_KEY_PATH
        self._old_env_key = os.environ.get("AC_MASTER_KEY")

        # 差し替え
        store_mod.USERS_JSON = self.users
        store_mod.SERVERS_JSON = self.servers
        store_mod.MASTER_KEY_PATH = self.mkey
        os.environ.pop("AC_MASTER_KEY", None)

        # 新しい SecretStore
        self.store = store_mod.SecretStore()
        return self

    def __exit__(self, exc_type, exc, tb):
        # 復元
        store_mod.USERS_JSON = self._old_USERS
        store_mod.SERVERS_JSON = self._old_SERVERS
        store_mod.MASTER_KEY_PATH = self._old_MKEY
        if self._old_env_key is not None:
            os.environ["AC_MASTER_KEY"] = self._old_env_key
        else:
            os.environ.pop("AC_MASTER_KEY", None)
        if self.root is not None:
            shutil.rmtree(self.root, ignore_errors=True)


def _writer_thread_user(store, uid: int, prov: str, payload: bytes) -> None:
    store.put_user_key(uid, prov, payload)


def _writer_thread_server(store, gid: int, prov: str, payload: bytes) -> None:
    store.put_server_key(gid, prov, payload)


class SecretStoreBasicTest(unittest.TestCase):
    """
    M01:T01-01 SecretStore 基本動作 & LWW 競合解決
    """

    def test_01_user_roundtrip(self):
        """[M01:T01-01-01] user鍵: put/get roundtrip"""
        with _TempStoreEnv() as env:
            ss = env.store
            assert ss is not None
            uid = 1234
            prov = "openai"
            token = b"TOKEN-USER"
            ss.put_user_key(uid, prov, token)
            got = ss.get_user_key(uid, prov)
            self.assertEqual(got, token)

    def test_02_server_roundtrip_and_delete(self):
        """[M01:T01-01-02] server鍵: roundtrip + has + delete"""
        with _TempStoreEnv() as env:
            ss = env.store
            assert ss is not None
            gid = 5678
            prov = "openai"
            token = b"TOKEN-SERVER"
            ss.put_server_key(gid, prov, token)
            self.assertTrue(ss.has_server_any_key(gid))
            self.assertEqual(ss.get_server_key(gid, prov), token)
            ss.delete_server_keys(gid)
            self.assertFalse(ss.has_server_any_key(gid))

    def test_03_user_concurrent_lww(self):
        """[M01:T01-01-03] user鍵: 並列 put -> LWW & 破損なし"""
        with _TempStoreEnv() as env:
            ss = env.store
            assert ss is not None
            uid = 999
            prov = "openai"
            t1 = threading.Thread(target=_writer_thread_user, args=(ss, uid, prov, b"AAA"))
            t2 = threading.Thread(target=_writer_thread_user, args=(ss, uid, prov, b"BBB"))
            t1.start()
            t2.start()
            t1.join()
            t2.join()
            last = ss.get_user_key(uid, prov)
            self.assertIn(last, (b"AAA", b"BBB"))

    def test_04_server_concurrent_lww(self):
        """[M01:T01-01-04] server鍵: 並列 put -> LWW & 破損なし"""
        with _TempStoreEnv() as env:
            ss = env.store
            assert ss is not None
            gid = 777
            prov = "openai"
            threads = [
                threading.Thread(
                    target=_writer_thread_server,
                    args=(ss, gid, prov, payload),
                )
                for payload in (b"111", b"222", b"333")
            ]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            last = ss.get_server_key(gid, prov)
            self.assertIn(last, (b"111", b"222", b"333"))


if __name__ == "__main__":
    mapping = {
        "test_01_user_roundtrip": ("COMMON-SECRET:T01-01-01", "user鍵: put/get roundtrip"),
        "test_02_server_roundtrip_and_delete": ("COMMON-SECRET:T01-01-02", "server鍵: roundtrip + has + delete"),
        "test_03_user_concurrent_lww": ("COMMON-SECRET:T01-01-03", "user鍵: 並列 put -> LWW"),
        "test_04_server_concurrent_lww": ("COMMON-SECRET:T01-01-04", "server鍵: 並列 put -> LWW"),
    }
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(SecretStoreBasicTest)
    run_unittest_suite("COMMON-SECRET:T01-01 common/secret/store", suite, mapping)
