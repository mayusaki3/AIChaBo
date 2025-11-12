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
import os
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

    def test_05_get_user_key_enc_missing_returns_none(self):
        """[M01:T01-04-05] get_user_key: enc不在 -> None"""
        with _TempRoot() as env:
            ss = store_mod.SecretStore()
            # users.json に provider はあるが enc が無い状態を作る
            env.users.write_text(json.dumps({"111": {"providers": {"openai": None}}}), encoding="utf-8")
            got = ss.get_user_key(111, "openai")
            self.assertIsNone(got)

    def test_06_delete_user_keys_true_branch(self):
        """[M01:T01-04-06] delete_user_keys: True 分岐"""
        with _TempRoot() as env:
            ss = store_mod.SecretStore()
            ss.put_user_key(1, "openai", b"X")
            ok = ss.delete_user_keys(1)
            self.assertTrue(ok)
            # 削除済みのため get_user_keys は {}（または None相当）
            self.assertEqual(ss.get_user_keys(1), {})

    def test_07_load_json_path_not_exists_returns_empty(self):
        """[M01:T01-04-07] _load_json: パス無し -> {}"""
        with _TempRoot() as env:
            ss = store_mod.SecretStore()
            # users.json を消しておく
            if env.users.exists():
                env.users.unlink()
            got = ss._load_json(env.users)
            self.assertEqual(got, {})

    def test_08_dec_empty_valueerror_handled_via_get_user_key(self):
        """[M01:T01-04-08] _dec('') の ValueError を get_user_key 側で握りつぶす経路"""
        with _TempRoot() as env:
            ss = store_mod.SecretStore()
            # 復号対象が空文字になるように直書き
            env.users.write_text(json.dumps({"222": {"providers": {"openai": ""}}}), encoding="utf-8")
            got = ss.get_user_key(222, "openai")
            self.assertIsNone(got)

    def test_09_load_json_recovery_save_fails(self):
        """[M01:T01-04-09] _load_json: 壊れJSON + 復旧saveも失敗 -> {} 返却"""
        with _TempRoot() as env:
            ss = store_mod.SecretStore()
            env.users.write_text("{broken json", encoding="utf-8")
            # _save_json 内部の置換で失敗させる
            real_replace = os.replace
            try:
                def boom(*a, **k):
                    raise OSError("fail replace")
                os.replace = boom
                got = ss._load_json(env.users)
                self.assertEqual(got, {})
            finally:
                os.replace = real_replace

    def test_10_save_json_cleanup_remove_raises(self):
        """[M01:T01-04-10] _save_json: finally cleanup の os.remove が例外でも漏れない"""
        with _TempRoot() as env:
            ss = store_mod.SecretStore()
            # json.dump を成功させ replace も通すが、最後の remove だけ落とす
            real_remove = os.remove
            try:
                def boom(path):
                    raise OSError("remove failed")
                os.remove = boom
                ss._save_json(env.users, {"a": 1})
            finally:
                os.remove = real_remove
            # tmp が残っていないことのみ確認
            leftovers = list(env.root.glob(env.users.name + ".*.tmp")) if env.root else []
            self.assertEqual(leftovers, [])

    def test_11_dec_empty_direct_raises_valueerror(self):
        """[M01:T01-04-11] _dec('') を直接叩く -> ValueError"""
        with _TempRoot() as _:
            ss = store_mod.SecretStore()
            with self.assertRaises(ValueError):
                ss._dec("")

    def test_12_delete_user_keys_both_branches(self):
        """[M01:T01-04-12] delete_user_keys: False -> True の両枝"""
        with _TempRoot() as env:
            ss = store_mod.SecretStore()
            # まず存在しない -> False
            self.assertFalse(ss.delete_user_keys(999))
            # 追加してから -> True
            ss.put_user_key(999, "openai", b"X")
            self.assertTrue(ss.delete_user_keys(999))


if __name__ == "__main__":
    mapping = {
        "test_01_get_user_keys_partial_success": ("M01:T01-04-01", "get_user_keys 部分成功"),
        "test_02_get_server_keys_missing_gid": ("M01:T01-04-02", "get_server_keys gid無し->{}"),
        "test_03_save_json_success": ("M01:T01-04-03", "_save_json 正常系"),
        "test_04_save_json_type_error_cleanup": ("M01:T01-04-04", "_save_json TypeError時cleanup"),
        "test_05_get_user_key_enc_missing_returns_none": ("M01:T01-04-05", "get_user_key: enc不在->None"),
        "test_06_delete_user_keys_true_branch": ("M01:T01-04-06", "delete_user_keys True分岐"),
        "test_07_load_json_path_not_exists_returns_empty": ("M01:T01-04-07", "_load_json パス無し->{}"),
        "test_08_dec_empty_valueerror_handled_via_get_user_key": ("M01:T01-04-08", "_dec('') ValueErrorをget_user_keyで握り潰す"),
        "test_09_load_json_recovery_save_fails": ("M01:T01-04-09", "壊れJSON+復旧save失敗->{}"),
        "test_10_save_json_cleanup_remove_raises": ("M01:T01-04-10", "_save_json cleanup remove例外"),
        "test_11_dec_empty_direct_raises_valueerror": ("M01:T01-04-11", "_dec('') 直接 -> ValueError"),
        "test_12_delete_user_keys_both_branches": ("M01:T01-04-12", "delete_user_keys false/true両枝"),
    }
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(SecretStoreMiscTest)
    run_unittest_suite("M01:T01-04", suite, mapping)
