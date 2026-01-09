# tests/common/secret/T01_SecretStore_05impl_store_misc_test.py
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import common.secret.store as store_mod
from common.secret.store import SecretStore
from tests._report import run_unittest_suite


def _temp_paths() -> tuple[Path, Path, Path, Path]:
    root = Path(tempfile.mkdtemp(prefix="aichabo_secretstore_t01_05_"))
    store_dir = root / "secretstore"
    store_dir.mkdir(parents=True, exist_ok=True)
    users = store_dir / "users.json"
    servers = store_dir / "servers.json"
    mkey = root / "master.key"
    return root, users, servers, mkey


class SecretStoreImplMiscTest(unittest.TestCase):
    """
    実装枝（カバレッジ）到達を目的としたテスト。
    仕様の正は docs ではなく、mapping（テストID定義）を正とする。
    """

    def setUp(self) -> None:
        self.root, self.users, self.servers, self.master_key = _temp_paths()

        self.p_users = patch.object(store_mod, "USERS_JSON", self.users)
        self.p_servers = patch.object(store_mod, "SERVERS_JSON", self.servers)
        self.p_mkey = patch.object(store_mod, "MASTER_KEY_PATH", self.master_key)
        self.p_users.start()
        self.p_servers.start()
        self.p_mkey.start()

        self.ss = SecretStore()

    def tearDown(self) -> None:
        self.p_users.stop()
        self.p_servers.stop()
        self.p_mkey.stop()
        try:
            for p in sorted(self.root.rglob("*"), reverse=True):
                try:
                    p.unlink()
                except Exception:
                    pass
            try:
                self.root.rmdir()
            except Exception:
                pass
        except Exception:
            pass

    def test_01_backend_name_matches_impl(self) -> None:
        name = self.ss.backend_name()
        self.assertIsInstance(name, str)
        self.assertTrue(name.strip())

    def test_02_dec_empty_raises_value_error_branch(self) -> None:
        with self.assertRaises(ValueError):
            self.ss._dec("")  # type: ignore[arg-type]

    def test_03_load_json_missing_path_returns_empty_branch(self) -> None:
        missing = self.root / "no_such_file.json"
        self.assertEqual(self.ss._load_json(missing), {})

    def test_04_load_json_recovery_save_fails_is_ignored_branch(self) -> None:
        p = self.root / "broken.json"
        p.write_text("{ this is not json", encoding="utf-8")

        with patch.object(SecretStore, "_save_json", side_effect=RuntimeError("boom")):
            got = self.ss._load_json(p)

        self.assertEqual(got, {})

    def test_05_save_json_cleanup_replace_fails_but_cleanup_runs(self) -> None:
        """
        os.replace 失敗 → 例外は出るが finally cleanup には入る。
        """
        p = self.root / "x.json"

        def _fake_replace(_src: str, _dst: str) -> None:
            raise OSError("replace failed")

        with patch.object(os, "replace", side_effect=_fake_replace):
            with self.assertRaises(OSError):
                self.ss._save_json(p, {"a": 1})

    # 追加（missing 行到達）

    def test_06_delete_user_keys_node_exists_but_providers_empty_returns_false(self) -> None:
        raw = {"1": {"providers": {}}}
        self.users.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
        self.assertFalse(self.ss.delete_user_keys(1))

    def test_07_delete_user_keys_save_failure_returns_false(self) -> None:
        raw = {"1": {"providers": {"openai": "fernet:INVALID_BUT_NONEMPTY"}}}
        self.users.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")

        with patch.object(SecretStore, "_save_json", side_effect=RuntimeError("boom")):
            self.assertFalse(self.ss.delete_user_keys(1))

    def test_08_delete_server_keys_node_exists_but_providers_empty_returns_false(self) -> None:
        raw = {"2": {"providers": {}}}
        self.servers.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
        self.assertFalse(self.ss.delete_server_keys(2))

    def test_09_delete_server_keys_save_failure_returns_false(self) -> None:
        raw = {"2": {"providers": {"openai": "fernet:INVALID_BUT_NONEMPTY"}}}
        self.servers.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")

        with patch.object(SecretStore, "_save_json", side_effect=RuntimeError("boom")):
            self.assertFalse(self.ss.delete_server_keys(2))

    def test_10_save_json_cleanup_os_remove_failure_is_ignored_branch(self) -> None:
        """
        _save_json finally の tmp cleanup で os.remove が例外でも握りつぶす。
        """
        p = self.root / "y.json"

        def _fake_replace(_src: str, _dst: str) -> None:
            raise OSError("replace failed")

        with patch.object(os, "replace", side_effect=_fake_replace), patch.object(
            os.path, "exists", return_value=True
        ), patch.object(os, "remove", side_effect=OSError("remove failed")):
            with self.assertRaises(OSError):
                self.ss._save_json(p, {"a": 1})


# テスト名 -> (番号, 説明)  ※ _report.py は test.id().split(".")[-1] をキーに引く
mapping = {
    "test_01_backend_name_matches_impl":
        ("COMMON-SECRET:T01-05-01", "backend_name が実装名を返す"),
    "test_02_dec_empty_raises_value_error_branch":
        ("COMMON-SECRET:T01-05-02", "_dec('') は ValueError"),
    "test_03_load_json_missing_path_returns_empty_branch":
        ("COMMON-SECRET:T01-05-03", "_load_json: パス無し -> {}"),
    "test_04_load_json_recovery_save_fails_is_ignored_branch":
        ("COMMON-SECRET:T01-05-04", "_load_json: 破損JSON→復旧save失敗でも {} を返す"),
    "test_05_save_json_cleanup_replace_fails_but_cleanup_runs":
        ("COMMON-SECRET:T01-05-05", "_save_json: os.replace 失敗でも cleanup に入る"),
    "test_06_delete_user_keys_node_exists_but_providers_empty_returns_false":
        ("COMMON-SECRET:T01-05-06", "delete_user_keys: providers 空 -> False"),
    "test_07_delete_user_keys_save_failure_returns_false":
        ("COMMON-SECRET:T01-05-07", "delete_user_keys: _save_json 例外 -> False"),
    "test_08_delete_server_keys_node_exists_but_providers_empty_returns_false":
        ("COMMON-SECRET:T01-05-08", "delete_server_keys: providers 空 -> False"),
    "test_09_delete_server_keys_save_failure_returns_false":
        ("COMMON-SECRET:T01-05-09", "delete_server_keys: _save_json 例外 -> False"),
    "test_10_save_json_cleanup_os_remove_failure_is_ignored_branch":
        ("COMMON-SECRET:T01-05-10", "_save_json: cleanup os.remove 例外を握りつぶす"),
}

if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(SecretStoreImplMiscTest)
    run_unittest_suite("COMMON-SECRET:T01-05 (impl) common/secret/store", suite, mapping)
