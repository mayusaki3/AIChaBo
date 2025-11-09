# tests/common/secret/T01_SecretStore_04_store_misc_test.py
# ------------------------------------------------------------
# M01:T01-04 : SecretStore misc branches (fill remaining holes)
# カバー目的：
#  - get_user_keys: 一部OK/一部NGの「部分成功」分岐（line 109 近辺）
#  - get_server_keys: gid 未登録 -> {}（132-134）
#  - _save_json: 正常系（成功置換で tmp なし）（193 or 204 の片枝）
#  - _save_json: json.dump 失敗（TypeError）-> 例外 + finally で tmp 後始末（236-237）
#  - _ensure_dir: 既存パスの分岐（213-214）
#
# 既存の M01:T01-02 / M01:T01-03 と同様、実ストアを汚さないために
# モジュール定数を temp へ差し替えてから SecretStore() を新規構築する。

import os
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from tests._report import _Reporter as Reporter
import common.secret.store as mod

rep = Reporter("M01:T01-04 SecretStore misc branches")

def _temp_paths():
    root = Path(tempfile.mkdtemp(prefix="aichabo_ss_misc_"))
    store_dir = root / "secretstore"
    # _ensure_dir の「存在している」枝も踏むため、最初から作っておく
    store_dir.mkdir(parents=True, exist_ok=True)
    return SimpleNamespace(
        root=root,
        store_dir=store_dir,
        users=store_dir / "users.json",
        servers=store_dir / "servers.json",
        mkey=root / "master.key",
    )

class SecretStoreMiscTest(unittest.TestCase):
    def setUp(self):
        self.paths = _temp_paths()
        # モジュール定数退避・差し替え
        self._old_USERS = mod.USERS_JSON
        self._old_SERVERS = mod.SERVERS_JSON
        self._old_MKEY = mod.MASTER_KEY_PATH
        self._old_env = os.environ.get("AC_MASTER_KEY")

        mod.USERS_JSON = self.paths.users
        mod.SERVERS_JSON = self.paths.servers
        mod.MASTER_KEY_PATH = self.paths.mkey
        if "AC_MASTER_KEY" in os.environ:
            del os.environ["AC_MASTER_KEY"]

        # 新規インスタンス（store シングルトンに依存しない）
        self.ss = mod.SecretStore()

    def tearDown(self):
        # 復元
        mod.USERS_JSON = self._old_USERS
        mod.SERVERS_JSON = self._old_SERVERS
        mod.MASTER_KEY_PATH = self._old_MKEY
        if self._old_env is not None:
            os.environ["AC_MASTER_KEY"] = self._old_env
        else:
            os.environ.pop("AC_MASTER_KEY", None)
        shutil.rmtree(self.paths.root, ignore_errors=True)

    # M01:T01-04-01: get_user_keys 部分成功（openai=OK / claude=破損 -> 除外）
    def test_01_get_user_keys_partial_success(self):
        ok = self.ss._enc(b"OK")
        bad = "fernet:INVALID"
        data = {
            "321": {"providers": {"openai": ok, "claude": bad}}
        }
        self.paths.users.write_text(json.dumps(data), encoding="utf-8")
        got = self.ss.get_user_keys(321)
        self.assertEqual(got, {"openai": b"OK"})

    # M01:T01-04-02: get_server_keys 未登録 gid -> {}
    def test_02_get_server_keys_missing_gid(self):
        self.assertEqual(self.ss.get_server_keys(999999), {})

    # M01:T01-04-03: _save_json 正常系（tmp->本体 置換成功で tmp 不要）
    def test_03_save_json_success_path(self):
        # 正常に書けるデータ
        payload = {"k": "v"}
        self.ss._save_json(self.paths.users, payload)
        text = self.paths.users.read_text(encoding="utf-8")
        self.assertIn('"k": "v"', text)
        # tmp が残っていないこと（正常分岐）
        tmp_candidates = list(self.paths.store_dir.glob(self.paths.users.name + ".*.tmp"))
        self.assertEqual(tmp_candidates, [])

    # M01:T01-04-04: _save_json で json.dump が TypeError -> 例外 + tmp 後始末（finally）
    def test_04_save_json_dump_typeerror_cleanup(self):
        class BadObj:
            # json が直列化できないオブジェクト
            pass

        # json.dump に到達させるため、os.replace は正常のまま。
        with self.assertRaises(TypeError):
            self.ss._save_json(self.paths.users, {"bad": BadObj()})
        # 例外後に tmp が残っていないこと（finally の cleanup）
        leftover = list(self.paths.store_dir.glob(self.paths.users.name + ".*.tmp"))
        self.assertEqual(leftover, [])

    # M01:T01-04-05: get_user_key で enc が存在しない分岐（line 109）
    def test_05_get_user_key_provider_missing_hits_enc_none(self):
        # users.json は空（既定） → 指定 provider が存在しない
        got = self.ss.get_user_key(123456, "openai")
        self.assertIsNone(got)

    # M01:T01-04-06: delete_user_keys の「存在時」分岐（132-134）
    def test_06_delete_user_keys_true_branch(self):
        self.ss.put_user_key(111, "openai", b"TOKEN")
        # 事前確認：何か入っている
        self.assertIn("openai", self.ss.get_user_keys(111))
        # 削除で providers を空にする分岐を踏む
        self.ss.delete_user_keys(111)
        self.assertEqual(self.ss.get_user_keys(111), {})

    # M01:T01-04-07: _load_json: パス自体が無い → {} を返す（line 204）
    def test_07_load_json_missing_path_direct(self):
        # 既存の Store とは別の、存在しない JSON パスを直接指定
        missing = self.paths.store_dir / "nonexists.json"
        out = self.ss._load_json(missing)
        self.assertEqual(out, {})

    # M01:T01-04-08: _dec("") → ValueError（line 193）を get_user_key 経由で踏む
    def test_08_dec_empty_raises_then_get_user_key_handles(self):
        # 復号不可（空文字）のエントリを直書き
        self.paths.users.write_text(
            json.dumps({"222": {"providers": {"openai": ""}}}),
            encoding="utf-8",
        )
        got = self.ss.get_user_key(222, "openai")
        self.assertIsNone(got)  # 例外は内部で握りつぶされ None

    # M01:T01-04-09: _load_json で JSON 壊れ → 復旧 save も失敗（213-214 の except 経路）
    def test_09_load_json_recovery_but_save_fails(self):
        # 壊れ JSON を用意
        self.paths.users.write_text("{broken json", encoding="utf-8")
        # save を内部で使うので os.replace を落として _save_json を失敗させる
        real_replace = mod.os.replace
        try:
            def bad_replace(src, dst): raise OSError("replace fails")
            mod.os.replace = bad_replace
            # ここで _load_json が失敗→復旧→_save_json 失敗→(213-214)pass
            out = self.ss._load_json(self.paths.users)
            self.assertEqual(out, {})  # 復旧失敗でも {} を返す想定
        finally:
            mod.os.replace = real_replace

    # M01:T01-04-10: _save_json の finally クリーンアップで os.remove が失敗（236-237）
    def test_10_save_json_cleanup_remove_error(self):
        # os.replace を失敗させて tmp を残し、さらに os.remove も失敗させる
        real_replace, real_remove = mod.os.replace, mod.os.remove
        def bad_replace(src, dst): raise OSError("replace fails")
        def bad_remove(path): raise OSError("remove fails")
        mod.os.replace = bad_replace
        mod.os.remove  = bad_remove
        try:
            with self.assertRaises(OSError):
                self.ss._save_json(self.paths.users, {"x": 1})
        finally:
            mod.os.replace = real_replace
            mod.os.remove  = real_remove

    # M01:T01-04-11: _dec("") を直叩きして line 193 を踏む（ValueError）
    def test_11_dec_direct_empty_raises(self):
        with self.assertRaises(ValueError):
            self.ss._dec("")  # get_user_key経由では109で早期returnされるため直叩き

    # M01:T01-04-12: delete_user_keys の false/true 両枝を踏む（132-134）
    def test_12_delete_user_keys_both_branches(self):
        # false-branch: まだユーザーが存在しない → if に入らないが save は走る
        self.ss.delete_user_keys(999001)
        self.assertEqual(self.ss.get_user_keys(999001), {})
        # true-branch: いったん作ってから消す → if に入って providers を clear
        self.ss.put_user_key(999002, "openai", b"T")
        self.assertIn("openai", self.ss.get_user_keys(999002))
        self.ss.delete_user_keys(999002)
        self.assertEqual(self.ss.get_user_keys(999002), {})


if __name__ == "__main__":
    print("=== M01:T01-04 SecretStore misc branches ===")
    cases = [
        ("test_01_get_user_keys_partial_success", "get_user_keys partial success"),
        ("test_02_get_server_keys_missing_gid",   "get_server_keys missing gid -> {}"),
        ("test_03_save_json_success_path",       "_save_json success path"),
        ("test_04_save_json_dump_typeerror_cleanup", "_save_json dump TypeError -> cleanup"),
        ("test_05_get_user_key_provider_missing_hits_enc_none", "get_user_key: enc missing -> None"),
        ("test_06_delete_user_keys_true_branch", "delete_user_keys true-branch"),
        ("test_07_load_json_missing_path_direct", "_load_json: path not exists -> {}"),
        ("test_08_dec_empty_raises_then_get_user_key_handles", "_dec('') -> ValueError handled"),
        ("test_09_load_json_recovery_but_save_fails", "_load_json: recovery save fails"),
        ("test_10_save_json_cleanup_remove_error", "_save_json: remove() fails in finally"),
        ("test_11_dec_direct_empty_raises", "_dec('') direct -> ValueError (hit line 193)"),
        ("test_12_delete_user_keys_both_branches", "delete_user_keys false & true branches (132-134)"),
    ]
    for meth, title in cases:
        with rep.case(title):
            tc = SecretStoreMiscTest(methodName=meth)
            try:
                tc.setUp()
                getattr(tc, meth)()
            finally:
                try:
                    tc.tearDown()
                except Exception:
                    pass
    rep.summary()
