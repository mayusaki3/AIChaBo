# -*- coding: utf-8 -*-
"""
M01:T01-03 SecretStore Init & Errors

- AC_MASTER_KEY 環境変数優先
- env 無し時の master.key 自動生成 + chmod 例外経路
- _load_json: パス無 → {}
- 復号不可トークンのスキップ（user/server）
- 未知 provider -> None
- _save_json: os.replace 失敗時の tmp 後始末

実行:
    python -m tests.common.secret.T01_SecretStore_03_store_init_test
"""

import json
import os
import stat
import tempfile
from pathlib import Path
import unittest

from cryptography.fernet import Fernet

from common.secret import store as mod
from tests._report import run_unittest_suite


class _TempRoot:
    """SecretStore 用一時ルート + users/servers パス."""

    def __init__(self) -> None:
        self.root: Path | None = None
        self.users: Path | None = None
        self.servers: Path | None = None
        self._orig_dir = os.environ.get("AIChaBo_SECRET_DIR")

    def __enter__(self) -> "_TempRoot":
        self.root = Path(tempfile.mkdtemp(prefix="secretstore-init-"))
        os.environ["AIChaBo_SECRET_DIR"] = str(self.root)
        self.users = self.root / "users.json"
        self.servers = self.root / "servers.json"
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._orig_dir is None:
            os.environ.pop("AIChaBo_SECRET_DIR", None)
        else:
            os.environ["AIChaBo_SECRET_DIR"] = self._orig_dir
        if self.root and self.root.exists():
            for p in self.root.iterdir():
                p.unlink(missing_ok=True)
            self.root.rmdir()


class SecretStoreInitTest(unittest.TestCase):
    """T01-03: 初期化と異常系分岐."""

    # M01:T01-03-01: AC_MASTER_KEY 優先 / master.key 不生成
    def test_01_init_with_env_key_no_master_file(self) -> None:
        with _TempRoot() as env:
            key = Fernet.generate_key().decode("ascii")
            os.environ["AC_MASTER_KEY"] = key
            try:
                ss = mod.SecretStore()
                # master.key は作られない想定
                assert env.root is not None
                master = env.root / "master.key"
                self.assertFalse(master.exists())
                # envキーで正常動作しているか、軽くR/Wで確認
                ss.put_user_key(1, "openai", b"X")  # noqa: SLF001
                self.assertEqual(ss.get_user_key(1, "openai"), b"X")
            finally:
                os.environ.pop("AC_MASTER_KEY", None)

    # M01:T01-03-02: env 無し → master.key 自動生成 / chmod 例外経路
    def test_02_init_without_env_generates_masterkey(self) -> None:
        with _TempRoot() as env:
            os.environ.pop("AC_MASTER_KEY", None)

            orig_chmod = os.chmod

            def bad_chmod(path, mode):
                raise PermissionError("chmod fail")

            os.chmod = bad_chmod  # type: ignore[assignment]
            try:
                ss = mod.SecretStore()
            finally:
                os.chmod = orig_chmod  # type: ignore[assignment]

            assert env.root is not None
            master = env.root / "master.key"
            # chmod 失敗しても master.key 自体は存在している想定
            self.assertTrue(master.exists())
            # 生成鍵で通常通り暗号化できているか軽く確認
            ss.put_server_key(1, "openai", b"Y")  # noqa: SLF001
            self.assertEqual(ss.get_server_key(1, "openai"), b"Y")

    # M01:T01-03-03: _load_json: パス未作成 -> {}
    def test_03_load_json_when_path_not_exists(self) -> None:
        with _TempRoot() as env:
            assert env.users is not None
            # users.json 未作成のまま SecretStore を初期化
            ss = mod.SecretStore()
            # 直接内部APIを叩く必要はなく、公開API経由で {} 相当を確認
            self.assertIsNone(ss.get_user_key(99999, "openai"))

    # M01:T01-03-04: 破損トークン（user）→ スキップ
    def test_04_corrupted_cipher_is_skipped_user(self) -> None:
        with _TempRoot() as env:
            assert env.users is not None
            ss = mod.SecretStore()
            data = {
                "12345": {
                    "providers": {
                        "openai": "fernet:INVALID",
                        "claude": "fernet:ALSO_BAD",
                    }
                }
            }
            env.users.write_text(json.dumps(data), encoding="utf-8")
            # 再読み込み
            ss = mod.SecretStore()
            self.assertIsNone(ss.get_user_key(12345, "openai"))
            self.assertEqual(ss.get_user_keys(12345), {})

    # M01:T01-03-05: 破損トークン（server）→ 正常分のみ残る
    def test_05_server_keys_skip_only_corrupt_entries(self) -> None:
        with _TempRoot() as env:
            assert env.servers is not None
            ss = mod.SecretStore()
            good = ss._enc(b"OK")  # noqa: SLF001
            data = {
                "777": {
                    "providers": {
                        "openai": good,
                        "gemini": "fernet:BAD",
                    }
                }
            }
            env.servers.write_text(json.dumps(data), encoding="utf-8")
            ss = mod.SecretStore()
            self.assertEqual(ss.get_server_keys(777), {"openai": b"OK"})

    # M01:T01-03-06: 未知 provider -> None
    def test_06_get_server_key_unknown_provider_none(self) -> None:
        with _TempRoot():
            ss = mod.SecretStore()
            self.assertIsNone(ss.get_server_key(1, "unknown"))

    # M01:T01-03-07: _save_json: os.replace 失敗時に tmp を掃除
    def test_07_save_json_tmp_cleanup_on_error(self) -> None:
        with _TempRoot() as env:
            ss = mod.SecretStore()
            assert env.users is not None
            # tmp を残さずに例外を返すことを確認
            class Boom(Exception):
                pass

            real_replace = mod.os.replace  # type: ignore[attr-defined]

            def bad_replace(src, dst):
                raise Boom()

            mod.os.replace = bad_replace  # type: ignore[assignment, attr-defined]
            try:
                with self.assertRaises(Boom):
                    ss._save_json(env.users, {"x": 1})  # noqa: SLF001
            finally:
                mod.os.replace = real_replace  # type: ignore[assignment, attr-defined]

            assert env.root is not None
            tmp_files = list(env.root.glob("*.tmp"))
            self.assertEqual(tmp_files, [])


if __name__ == "__main__":
    mapping = {
        "test_01_init_with_env_key_no_master_file":
            ("M01:T01-03-01", "env優先: master.key未生成"),
        "test_02_init_without_env_generates_masterkey":
            ("M01:T01-03-02", "env無し: master.key生成 + chmod例外経路"),
        "test_03_load_json_when_path_not_exists":
            ("M01:T01-03-03", "_load_json: pathなし -> {}"),
        "test_04_corrupted_cipher_is_skipped_user":
            ("M01:T01-03-04", "破損トークン(user)はスキップ"),
        "test_05_server_keys_skip_only_corrupt_entries":
            ("M01:T01-03-05", "破損トークン(server)はスキップ"),
        "test_06_get_server_key_unknown_provider_none":
            ("M01:T01-03-06", "未知provider -> None"),
        "test_07_save_json_tmp_cleanup_on_error":
            ("M01:T01-03-07", "_save_json: 失敗時tmp削除"),
    }
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(SecretStoreInitTest)
    run_unittest_suite("M01:T01-03", suite, mapping)
