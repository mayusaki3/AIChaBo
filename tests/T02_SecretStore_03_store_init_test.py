# tests/T02_SecretStore_03_store_init_test.py
# ------------------------------------------------------------
# T02-03 : SecretStore init / key-gen / error paths
# 目的:
#  - AC_MASTER_KEY 環境変数の有無での初期化分岐
#  - master.key 自動生成＋chmod 例外経路
#  - _load_json: パスが存在しない場合の {} 戻り
#  - 破損トークンのスキップ（get_user_key / get_user_keys / get_server_keys）
#  - _save_json: os.replace 失敗時に tmp を後始末（finally 経路）
#
# 手法:
#  - common.secret.store モジュールのパス定数を temp へ差し替え
#  - その上で SecretStore() を新規生成（store シングルトンは触らない）
#  - monkeypatch で os.chmod / os.replace を一時差し替え

import os
import json
import stat
import shutil
import tempfile
import unittest
import importlib
from pathlib import Path

from tests._report import _Reporter as Reporter

import common.secret.store as mod  # モジュール参照（定数を差し替えるため）

rep = Reporter("T02-03 SecretStore init & errors")


def _temp_paths():
    root = Path(tempfile.mkdtemp(prefix="aichabo_ss_init_"))
    store_dir = root / "secretstore"
    store_dir.mkdir(parents=True, exist_ok=True)
    users = store_dir / "users.json"
    servers = store_dir / "servers.json"
    mkey = root / "master.key"
    return root, users, servers, mkey


class SecretStoreInitTest(unittest.TestCase):
    def setUp(self):
        # temp へ差し替え
        self.root, self.users, self.servers, self.mkey = _temp_paths()
        self._old_USERS = mod.USERS_JSON
        self._old_SERVERS = mod.SERVERS_JSON
        self._old_MKEY = mod.MASTER_KEY_PATH
        mod.USERS_JSON = self.users
        mod.SERVERS_JSON = self.servers
        mod.MASTER_KEY_PATH = self.mkey

        # env 退避
        self._old_env_key = os.environ.get("AC_MASTER_KEY")
        if "AC_MASTER_KEY" in os.environ:
            del os.environ["AC_MASTER_KEY"]

    def tearDown(self):
        # env 復元
        if self._old_env_key is not None:
            os.environ["AC_MASTER_KEY"] = self._old_env_key
        else:
            os.environ.pop("AC_MASTER_KEY", None)

        # パス定数復元
        mod.USERS_JSON = self._old_USERS
        mod.SERVERS_JSON = self._old_SERVERS
        mod.MASTER_KEY_PATH = self._old_MKEY

        # temp 後片付け
        shutil.rmtree(self.root, ignore_errors=True)

    # T02-03-01: AC_MASTER_KEY あり → master.key を作らずに初期化
    def test_01_init_with_env_key(self):
        # Fernet キー文字列（32byte base64）
        from cryptography.fernet import Fernet
        os.environ["AC_MASTER_KEY"] = Fernet.generate_key().decode()

        ss = mod.SecretStore()
        self.assertFalse(self.mkey.exists(), "env優先のため master.key は作られない")
        self.assertIn("Fernet", ss.backend_name())

        # 最低限のR/Wが動くか
        ss.put_user_key(100, "openai", b"envtok")
        self.assertEqual(ss.get_user_key(100, "openai"), b"envtok")

    # T02-03-02: envなし → master.key を生成、chmod 例外経路を踏む
    def test_02_init_generates_masterkey_and_handles_chmod_error(self):
        # os.chmod を例外を投げるダミーにする（except経路）
        real_chmod = os.chmod
        def bad_chmod(path, mode): raise OSError("perm error")
        os.chmod = bad_chmod
        try:
            ss = mod.SecretStore()
        finally:
            os.chmod = real_chmod

        self.assertTrue(self.mkey.exists(), "env無しなので master.key を生成する")
        # users.json / servers.json が初期化される
        self.assertTrue(self.users.exists())
        self.assertTrue(self.servers.exists())

    # T02-03-03: _load_json - ファイル未作成なら {} を返す
    def test_03_load_json_when_path_not_exists(self):
        # 明示的に削除して {} 経路へ
        if self.users.exists():
            self.users.unlink()
        ss = mod.SecretStore()
        # 直接内部APIを呼ぶ必要はなく、公開API越しに間接確認でもOK
        self.assertEqual(ss.get_user_keys(99999), {})

    # T02-03-04: 破損トークン（復号不可）→ get_user_key は None, get_user_keys はスキップ
    def test_04_corrupted_cipher_is_skipped(self):
        ss = mod.SecretStore()
        # users.json に復号できないトークンを書き込む
        data = {
            "12345": {
                "providers": {
                    "openai": "fernet:INVALIDTOKEN",
                    "claude": "fernet:ALSOINVALID"
                }
            }
        }
        self.users.write_text(json.dumps(data), encoding="utf-8")
        self.assertIsNone(ss.get_user_key(12345, "openai"))
        keys = ss.get_user_keys(12345)
        self.assertEqual(keys, {}, "すべて破損なら空辞書")

    # T02-03-05: get_server_keys - 片方だけ破損 → 正常分のみ残る
    def test_05_server_keys_skip_only_corrupt_entries(self):
        ss = mod.SecretStore()
        # 正常トークンを1つ作る
        good = ss._enc(b"OK")
        data = {
            "777": {
                "providers": {
                    "openai": good,
                    "gemini": "fernet:BAD"
                }
            }
        }
        self.servers.write_text(json.dumps(data), encoding="utf-8")
        got = ss.get_server_keys(777)
        self.assertEqual(got, {"openai": b"OK"})

    # T02-03-06: get_server_key - 不明provider → None
    def test_06_get_server_key_unknown_provider(self):
        ss = mod.SecretStore()
        self.assertIsNone(ss.get_server_key(555, "nope"))

    # T02-03-07: _save_json - os.replace が失敗 → finally で tmp を後始末
    def test_07_save_json_tmp_cleanup_on_replace_error(self):
        ss = mod.SecretStore()
        real_replace = mod.os.replace
        def bad_replace(src, dst): raise OSError("replace failed")
        mod.os.replace = bad_replace
        try:
            with self.assertRaises(OSError):
                # 内部API直叩き：例外で抜けた後、finallyで tmp が消される分岐を踏む
                ss._save_json(self.users, {"x": 1})
        finally:
            mod.os.replace = real_replace


if __name__ == "__main__":
    SUITE_TITLE = "T02-03 SecretStore init & errors"
    print(f"=== {SUITE_TITLE} ===")
    cases = [
        ("T02-03-01", "init with env key (no master.key)"),
        ("T02-03-02", "init w/o env -> master.key + chmod except"),
        ("T02-03-03", "_load_json: path not exists -> {}"),
        ("T02-03-04", "corrupt tokens are skipped (user)"),
        ("T02-03-05", "corrupt tokens are skipped (server)"),
        ("T02-03-06", "get_server_key unknown provider -> None"),
        ("T02-03-07", "_save_json replace-error -> tmp cleanup"),
    ]
    for meth, (_, title) in zip([
        "test_01_init_with_env_key",
        "test_02_init_generates_masterkey_and_handles_chmod_error",
        "test_03_load_json_when_path_not_exists",
        "test_04_corrupted_cipher_is_skipped",
        "test_05_server_keys_skip_only_corrupt_entries",
        "test_06_get_server_key_unknown_provider",
        "test_07_save_json_tmp_cleanup_on_replace_error",
    ], cases):
        with rep.case(title):
            # TestCase を手動実行するため setUp/tearDown を明示呼び出し
            tc = SecretStoreInitTest(methodName=meth)
            try:
                tc.setUp()
                getattr(tc, meth)()
            finally:
                # 例外時も確実に復元
                try:
                    tc.tearDown()
                except Exception:
                    pass
    rep.summary()
