# tests/common/secret/T01_SecretStore_03_store_init_test.py
# ------------------------------------------------------------
# M01:T01-03 : SecretStore init / key-gen / error paths
# 目的:
#  - AC_MASTER_KEY 環境変数の有無での初期化分岐
#  - master.key 自動生成＋chmod 例外経路
#  - _load_json: パスが存在しない場合の {} 戻りを間接確認
#  - 破損トークンのスキップ（user/server）
#  - _save_json: os.replace 失敗時に tmp を後始末（finally 経路）
#
# 方針:
#  - common.secret.store のパス定数を一時的に temp に差し替え
#  - AC_MASTER_KEY 環境変数をテスト毎に制御
#  - 旧版テストのロジックを維持しつつ、run_unittest_suite 形式に統一

import os
import json
import stat
import shutil
import tempfile
import unittest
from pathlib import Path

from cryptography.fernet import Fernet

from tests._report import run_unittest_suite
import common.secret.store as mod


def _temp_paths() -> tuple[Path, Path, Path, Path]:
    root = Path(tempfile.mkdtemp(prefix="aichabo_ss_init_"))
    store_dir = root / "secretstore"
    store_dir.mkdir(parents=True, exist_ok=True)
    users = store_dir / "users.json"
    servers = store_dir / "servers.json"
    mkey = root / "master.key"
    return root, users, servers, mkey


class SecretStoreInitTest(unittest.TestCase):
    def setUp(self) -> None:
        # SecretStore が参照するパス定数を temp へ差し替え
        self.root, self.users, self.servers, self.mkey = _temp_paths()

        self._old_USERS = mod.USERS_JSON
        self._old_SERVERS = mod.SERVERS_JSON
        self._old_MKEY = mod.MASTER_KEY_PATH

        mod.USERS_JSON = self.users
        mod.SERVERS_JSON = self.servers
        mod.MASTER_KEY_PATH = self.mkey

        # AC_MASTER_KEY を退避してクリア
        self._old_env_key = os.environ.get("AC_MASTER_KEY")
        if "AC_MASTER_KEY" in os.environ:
            del os.environ["AC_MASTER_KEY"]

    def tearDown(self) -> None:
        # 環境変数を元に戻す
        if self._old_env_key is not None:
            os.environ["AC_MASTER_KEY"] = self._old_env_key
        else:
            os.environ.pop("AC_MASTER_KEY", None)

        # パス定数を元に戻す
        mod.USERS_JSON = self._old_USERS
        mod.SERVERS_JSON = self._old_SERVERS
        mod.MASTER_KEY_PATH = self._old_MKEY

        # temp 削除
        shutil.rmtree(self.root, ignore_errors=True)

    # M01:T01-03-01: AC_MASTER_KEY あり → master.key を作らずに初期化
    def test_01_init_with_env_key(self):
        os.environ["AC_MASTER_KEY"] = Fernet.generate_key().decode()
        ss = mod.SecretStore()

        self.assertFalse(
            self.mkey.exists(),
            "env優先のため master.key は作られないはず",
        )
        # backend が正常に構成されている前提で、簡易に put/get を確認
        ss.put_user_key(100, "openai", b"envtok")
        self.assertEqual(ss.get_user_key(100, "openai"), b"envtok")

    # M01:T01-03-02: envなし → master.key を生成、chmod 例外経路を踏む
    def test_02_init_generates_masterkey_and_handles_chmod_error(self):
        # os.chmod を一時的に壊して except 経路を通す
        real_chmod = os.chmod

        def bad_chmod(path, mode):
            raise OSError("chmod failed")

        os.chmod = bad_chmod
        try:
            ss = mod.SecretStore()
        finally:
            os.chmod = real_chmod

        # master.key が生成されている
        self.assertTrue(self.mkey.exists())
        # users / servers の初期ファイルも存在してよい
        self.assertTrue(self.users.exists())
        self.assertTrue(self.servers.exists())

        # master.key のパーミッション確認（存在していることが主目的）
        st = self.mkey.stat()
        self.assertTrue(stat.S_ISREG(st.st_mode))

    # M01:T01-03-03: _load_json - パス未作成なら {} を返す (公開API越しの間接確認)
    def test_03_load_json_when_path_not_exists(self):
        # users.json を消しておき、新規 SecretStore から get_user_keys を呼ぶ
        if self.users.exists():
            self.users.unlink()

        ss = mod.SecretStore()
        self.assertEqual(
            ss.get_user_keys(99999),
            {},
            "_load_json がファイル無しで {} を返していることを間接確認",
        )

    # M01:T01-03-04: 破損 user トークンはスキップされる
    def test_04_corrupted_user_tokens_are_skipped(self):
        ss = mod.SecretStore()

        # 復号不可なトークンを書き込む
        data = {
            "12345": {
                "providers": {
                    "openai": "fernet:INVALID",
                    "claude": "fernet:ALSO_BAD",
                }
            }
        }
        self.users.write_text(json.dumps(data), encoding="utf-8")

        self.assertIsNone(ss.get_user_key(12345, "openai"))
        self.assertEqual(
            ss.get_user_keys(12345),
            {},
            "全て破損している場合は空 dict",
        )

    # M01:T01-03-05: 破損 server トークンはスキップされ、正常分のみ残る
    def test_05_server_keys_skip_only_corrupt_entries(self):
        ss = mod.SecretStore()

        good = ss._enc(b"OK")
        data = {
            "777": {
                "providers": {
                    "openai": good,
                    "gemini": "fernet:BAD",
                }
            }
        }
        self.servers.write_text(json.dumps(data), encoding="utf-8")

        got = ss.get_server_keys(777)
        self.assertEqual(got, {"openai": b"OK"})

    # M01:T01-03-06: 未知 provider -> None
    def test_06_get_server_key_unknown_provider(self):
        ss = mod.SecretStore()
        self.assertIsNone(ss.get_server_key(555, "nope"))

    # M01:T01-03-07: _save_json - os.replace 失敗時に tmp を削除
    def test_07_save_json_tmp_cleanup_on_replace_error(self):
        ss = mod.SecretStore()

        real_replace = mod.os.replace

        def bad_replace(src, dst):
            raise OSError("replace failed")

        mod.os.replace = bad_replace
        try:
            with self.assertRaises(OSError):
                ss._save_json(self.users, {"x": 1})

            # tmp ファイルが残っていないことを確認
            for p in self.users.parent.iterdir():
                self.assertFalse(
                    p.name.startswith(self.users.name + "."),
                    "os.replace 失敗後も tmp は削除されているべき",
                )
        finally:
            mod.os.replace = real_replace


# テスト名 -> (番号, 説明)
mapping = {
    "test_01_init_with_env_key":
        ("M01:T01-03-01", "env優先: master.key未生成"),
    "test_02_init_generates_masterkey_and_handles_chmod_error":
        ("M01:T01-03-02", "env無し: master.key生成 + chmod例外経路"),
    "test_03_load_json_when_path_not_exists":
        ("M01:T01-03-03", "_load_json: pathなし -> {}"),
    "test_04_corrupted_user_tokens_are_skipped":
        ("M01:T01-03-04", "破損トークン(user)はスキップ"),
    "test_05_server_keys_skip_only_corrupt_entries":
        ("M01:T01-03-05", "破損トークン(server)はスキップ"),
    "test_06_get_server_key_unknown_provider":
        ("M01:T01-03-06", "未知provider -> None"),
    "test_07_save_json_tmp_cleanup_on_replace_error":
        ("M01:T01-03-07", "_save_json: 失敗時tmp削除"),
}

if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(SecretStoreInitTest)
    run_unittest_suite("M01:T01-03", suite, mapping)
