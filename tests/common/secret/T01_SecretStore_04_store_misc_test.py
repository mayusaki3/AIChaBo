# tests/common/secret/T01_SecretStore_04_store_misc_test.py
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import common.secret.store as store_mod
from common.secret.store import SecretStore
from tests._report import run_unittest_suite


def _temp_paths() -> tuple[Path, Path, Path, Path]:
    root = Path(tempfile.mkdtemp(prefix="aichabo_secretstore_t01_04_"))
    store_dir = root / "secretstore"
    store_dir.mkdir(parents=True, exist_ok=True)
    users = store_dir / "users.json"
    servers = store_dir / "servers.json"
    mkey = root / "master.key"
    return root, users, servers, mkey


class SecretStoreMiscTest(unittest.TestCase):
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

        # 後片付け（失敗してもテスト結果に影響させない）
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

    def test_01_get_user_keys_partial_success(self) -> None:
        """get_user_keys: 破損トークン混在でも部分成功すること。"""
        self.ss.put_user_key("1", "openai", b"sk-AAAA")
        self.ss.put_user_key("1", "gemini", b"AIzaBBBB")

        # openai だけ破損させる
        raw = json.loads(self.users.read_text(encoding="utf-8"))
        raw.setdefault("1", {}).setdefault("providers", {})
        raw["1"]["providers"]["openai"] = "fernet:INVALID_TOKEN"
        self.users.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")

        got = self.ss.get_user_keys("1")
        self.assertIsInstance(got, dict)
        self.assertNotIn("openai", got)
        self.assertEqual(got.get("gemini"), b"AIzaBBBB")

    def test_02_get_server_keys_missing_gid_returns_empty(self) -> None:
        """get_server_keys: 未登録gid(None)なら {}。"""
        got = self.ss.get_server_keys(None)
        self.assertEqual(got, {})

    def test_03_put_server_key_overwrite(self) -> None:
        """put_server_key: 同一 gid/provider で上書きできる。"""
        self.ss.put_server_key("2", "openai", b"sk-OLD")
        self.ss.put_server_key("2", "openai", b"sk-NEW")
        got = self.ss.get_server_key("2", "openai")
        self.assertEqual(got, b"sk-NEW")

    def test_04_delete_empty_or_missing_is_safe_false(self) -> None:
        """delete_*: 空/欠落でも例外を出さず False。"""
        self.assertFalse(self.ss.delete_user_keys("1"))
        self.assertFalse(self.ss.delete_server_keys("2"))


# テスト名 -> (番号, 説明)
mapping = {
    "test_01_get_user_keys_partial_success":
        ("COMMON-SECRET:T01-04-01", "get_user_keys 部分成功（破損トークンはスキップ）"),
    "test_02_get_server_keys_missing_gid_returns_empty":
        ("COMMON-SECRET:T01-04-02", "get_server_keys gid無し->{}"),
    "test_03_put_server_key_overwrite":
        ("COMMON-SECRET:T01-04-03", "put_server_key 上書き"),
    "test_04_delete_empty_or_missing_is_safe_false":
        ("COMMON-SECRET:T01-04-04", "delete_* 空/欠落でもFalse（堅牢性）"),
}

if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(SecretStoreMiscTest)
    run_unittest_suite("COMMON-SECRET:T01-04 common/secret/store", suite, mapping)
