# -*- coding: utf-8 -*-
"""
M01:T01-04 SecretStore その他分岐

目的:
  - get_user_keys / get_server_keys の部分成功パス
  - _save_json 正常系 / dump 例外時のクリーンアップ
  - _dec の ValueError ハンドリング 等

実行例:
  python -m tests.common.secret.T01_SecretStore_04_store_misc_test
"""

import json
import tempfile
import shutil
import unittest
from pathlib import Path

from tests._report import run_unittest_suite
import common.secret.store as store_mod


class _TempRoot:
    def __init__(self) -> None:
        self.root: Path | None = None
        self.users: Path | None = None
        self.servers: Path | None = None
        self.mkey: Path | None = None
        self._old_USERS = None
        self._old_SERVERS = None
        self._old_MKEY = None

    def __enter__(self):
        self.root = Path(tempfile.mkdtemp(prefix="aichabo_ss_M01T01_04_"))
        self.users = self.root / "users.json"
        self.servers = self.root / "servers.json"
        self.mkey = self.root / "master.key"
        self._old_USERS = store_mod.USERS_JSON
        self._old_SERVERS = store_mod.SERVERS_JSON
        self._old_MKEY = store_mod.MASTER_KEY_PATH
        store_mod.USERS_JSON = self.users
        store_mod.SERVERS_JSON = self.servers
        store_mod.MASTER_KEY_PATH = self.mkey
        return self

    def __exit__(self, exc_type, exc, tb):
        store_mod.USERS_JSON = self._old_USERS
        store_mod.SERVERS_JSON = self._old_SERVERS
        store_mod.MASTER_KEY_PATH = self._old_MKEY
        if self.root is not None:
            shutil.rmtree(self.root, ignore_errors=True)


class SecretStoreMiscTest(unittest.TestCase):
    """
    M01:T01-04 SecretStore 細かい分岐
    """

    def test_01_get_user_keys_partial_success(self):
        """[M01:T01-04-01] 一部復号失敗しても残りは取得"""
        with _TempRoot() as env:
            ss = store_mod.SecretStore()
            assert env.users is not None
            # 正常 + 壊れ
            ss.put_user_key(1, "ok", b"OK")
            data = json.loads(env.users.read_text(encoding="utf-8"))
            data.setdefault("1", {})["bad"] = "not-base64"
            env.users.write_text(json.dumps(data), encoding="utf-8")

            out = ss.get_user_keys(1)
            self.assertEqual(out["ok"], b"OK")
            self.assertNotIn("bad", out)

    def test_02_get_server_keys_missing_gid(self):
        """[M01:T01-04-02] get_server_keys: 無いgid -> {}"""
        with _TempRoot():
            ss = store_mod.SecretStore()
            self.assertEqual(ss.get_server_keys(9999), {})

    def test_03_save_json_success(self):
        """[M01:T01-04-03] _save_json 正常系"""
        with _TempRoot() as env:
            ss = store_mod.SecretStore()
            assert env.users is not None
            ss._save_json(env.users, {"x": 1})  # noqa: SLF001
            data = json.loads(env.users.read_text(encoding="utf-8"))
            self.assertEqual(data, {"x": 1})

    def test_04_save_json_type_error_cleanup(self):
        """[M01:T01-04-04] _save_json dump TypeError -> tmp cleanup"""
        with _TempRoot() as env:
            ss = store_mod.SecretStore()
            assert env.users is not None

            class Dummy:
                pass

            with self.assertRaises(TypeError):
                ss._save_json(env.users, {"x": Dummy()})  # noqa: SLF001

            # tmp が残っていないことのみ確認
            tmp = list(env.root.glob("*.tmp")) if env.root else []
            self.assertEqual(tmp, [])


if __name__ == "__main__":
    mapping = {
        "test_01_get_user_keys_partial_success": ("M01:T01-04-01", "get_user_keys 部分成功"),
        "test_02_get_server_keys_missing_gid": ("M01:T01-04-02", "get_server_keys gid無し->{}"),
        "test_03_save_json_success": ("M01:T01-04-03", "_save_json 正常系"),
        "test_04_save_json_type_error_cleanup": ("M01:T01-04-04", "_save_json TypeError時cleanup"),
    }
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(SecretStoreMiscTest)
    run_unittest_suite("M01:T01-04", suite, mapping)
