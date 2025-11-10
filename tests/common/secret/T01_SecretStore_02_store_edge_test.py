# -*- coding: utf-8 -*-
"""
M01:T01-02 SecretStore Edge & Recovery

- 例外系・空入力分岐
- サーバー鍵存在判定 / 削除安全性
- 後方互換（'fernet:' 無しトークン）
- 壊れ JSON の self-heal
- ユーザー削除で providers 空化

実行:
    python -m tests.common.secret.T01_SecretStore_02_store_edge_test
"""

import json
import os
import tempfile
from pathlib import Path
import unittest

from common.secret import store as mod
from tests._report import run_unittest_suite


class _TempRoot:
    """SecretStore 用の一時ルートディレクトリを張るヘルパ."""

    def __init__(self) -> None:
        self.root: Path | None = None
        self.users: Path | None = None
        self.servers: Path | None = None
        self._orig_dir = os.environ.get("AIChaBo_SECRET_DIR")

    def __enter__(self) -> "_TempRoot":
        self.root = Path(tempfile.mkdtemp(prefix="secretstore-edge-"))
        # SecretStore はこの環境変数配下に users.json / servers.json 等を作る想定
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


class SecretStoreEdgeTest(unittest.TestCase):
    """T01-02: SecretStore の端・異常系と復旧経路."""

    # M01:T01-02-01: put_user_key("", ...) -> ValueError
    def test_01_put_user_empty_provider_raises_value_error(self) -> None:
        with _TempRoot():
            ss = mod.SecretStore()
            with self.assertRaises(ValueError):
                ss.put_user_key(1, "", b"X")  # noqa: SLF001

    # M01:T01-02-02: put_server_key("", ...) -> ValueError
    def test_02_put_server_empty_provider_raises_value_error(self) -> None:
        with _TempRoot():
            ss = mod.SecretStore()
            with self.assertRaises(ValueError):
                ss.put_server_key(1, "", b"X")  # noqa: SLF001

    # M01:T01-02-03: get_user_key("", ...) -> None
    def test_03_get_user_empty_provider_returns_none(self) -> None:
        with _TempRoot():
            ss = mod.SecretStore()
            self.assertIsNone(ss.get_user_key(1, ""))

    # M01:T01-02-04: get_server_key("", ...) -> None
    def test_04_get_server_empty_provider_returns_none(self) -> None:
        with _TempRoot():
            ss = mod.SecretStore()
            self.assertIsNone(ss.get_server_key(1, ""))

    # M01:T01-02-05: has_server_any_key False -> True
    def test_05_has_server_any_key_false_then_true(self) -> None:
        with _TempRoot():
            ss = mod.SecretStore()
            self.assertFalse(ss.has_server_any_key(10))
            ss.put_server_key(10, "openai", b"KEY")  # noqa: SLF001
            self.assertTrue(ss.has_server_any_key(10))

    # M01:T01-02-06: delete_server_keys 非存在 gid でも安全
    def test_06_delete_server_keys_safe_for_missing_gid(self) -> None:
        with _TempRoot():
            ss = mod.SecretStore()
            # 無い gid でも例外なし
            ss.delete_server_keys(9999)
            # あった場合も削除されること
            ss.put_server_key(1, "openai", b"KEY")  # noqa: SLF001
            self.assertTrue(ss.has_server_any_key(1))
            ss.delete_server_keys(1)
            self.assertFalse(ss.has_server_any_key(1))

    # M01:T01-02-07: 後方互換 'fernet:' 無しトークンでも復号できること
    def test_07_backward_compat_no_prefix(self) -> None:
        with _TempRoot() as env:
            assert env.users is not None
            # 旧形式: プレーンなバイナリをそのまま保存していた想定
            data = {
                "1": {
                    "providers": {
                        "openai": "OLD",  # 'fernet:' プレフィックスなし
                    }
                }
            }
            env.users.write_text(json.dumps(data), encoding="utf-8")
            ss = mod.SecretStore()
            self.assertEqual(ss.get_user_key(1, "openai"), b"OLD")

    # M01:T01-02-08: 壊れ JSON -> self-heal で空に戻す
    def test_08_broken_json_is_recovered_to_empty(self) -> None:
        with _TempRoot() as env:
            assert env.users is not None
            env.users.write_text("{broken", encoding="utf-8")
            ss = mod.SecretStore()
            # 読み込み時に自動修復されている想定: エラーにならず None
            self.assertIsNone(ss.get_user_key(1, "openai"))
            # ファイル内容が有効JSON（空 dict）に置き換わっていること
            loaded = json.loads(env.users.read_text(encoding="utf-8"))
            self.assertEqual(loaded, {})

    # M01:T01-02-09: delete_user_keys で providers 空化
    def test_09_delete_user_keys_clears_all_keys(self) -> None:
        with _TempRoot():
            ss = mod.SecretStore()
            ss.put_user_key(1, "openai", b"A")  # noqa: SLF001
            ss.put_user_key(1, "claude", b"B")  # noqa: SLF001
            self.assertIsNotNone(ss.get_user_key(1, "openai"))
            self.assertIsNotNone(ss.get_user_key(1, "claude"))
            ss.delete_user_keys(1)
            self.assertIsNone(ss.get_user_key(1, "openai"))
            self.assertIsNone(ss.get_user_key(1, "claude"))


if __name__ == "__main__":
    mapping = {
        "test_01_put_user_empty_provider_raises_value_error":
            ("M01:T01-02-01", "put_user: provider空 -> ValueError"),
        "test_02_put_server_empty_provider_raises_value_error":
            ("M01:T01-02-02", "put_server: provider空 -> ValueError"),
        "test_03_get_user_empty_provider_returns_none":
            ("M01:T01-02-03", "get_user: provider空 -> None"),
        "test_04_get_server_empty_provider_returns_none":
            ("M01:T01-02-04", "get_server: provider空 -> None"),
        "test_05_has_server_any_key_false_then_true":
            ("M01:T01-02-05", "has_server_any_key False/True"),
        "test_06_delete_server_keys_safe_for_missing_gid":
            ("M01:T01-02-06", "delete_server_keys 安全"),
        "test_07_backward_compat_no_prefix":
            ("M01:T01-02-07", "旧prefixなし互換"),
        "test_08_broken_json_is_recovered_to_empty":
            ("M01:T01-02-08", "壊れJSON復旧"),
        "test_09_delete_user_keys_clears_all_keys":
            ("M01:T01-02-09", "delete_user_keys 全削除"),
    }
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(SecretStoreEdgeTest)
    run_unittest_suite("M01:T01-02", suite, mapping)
