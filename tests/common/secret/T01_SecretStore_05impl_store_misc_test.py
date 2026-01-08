"""
tests.common.secret.T01_SecretStore_05impl_store_misc_test

[テストユーティリティ](../../README_TEST.md) > common/secretモジュール単体テスト

本スイートは (impl) として、仕様テストでは要求しにくい分岐（例外ハンドリング等）の
カバレッジ到達を目的とする。mapping によるテストID出力が正であることも前提とする。
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests._report import run_unittest_suite

from common.secret import store as store_mod


class SecretStoreImplMiscTest(unittest.TestCase):
    """
    COMMON-SECRET:T01-05 (impl) common/secret/store
    """

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)

        store_mod._BASE_DIR = self.base
        store_mod._USERS_PATH = self.base / "users.json"
        store_mod._SERVERS_PATH = self.base / "servers.json"
        store_mod._MASTER_KEY_PATH = self.base / "master.key"

        self.ss = store_mod.SecretStore()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_01_backend_name_matches_impl(self) -> None:
        """
        [COMMON-SECRET:T01-05-01] backend_name が実装名を返す
        """
        self.assertIsInstance(self.ss.backend_name(), str)
        self.assertTrue(len(self.ss.backend_name()) > 0)

    def test_02_dec_empty_raises_value_error_branch(self) -> None:
        """
        [COMMON-SECRET:T01-05-02] _dec('') は ValueError
        """
        with self.assertRaises(ValueError):
            self.ss._dec("")  # type: ignore[arg-type]

    def test_03_load_json_missing_path_returns_empty_branch(self) -> None:
        """
        [COMMON-SECRET:T01-05-03] _load_json: パス無し -> {}
        """
        missing = self.base / "missing.json"
        self.assertEqual(self.ss._load_json(missing), {})

    def test_04_load_json_recovery_save_fails_is_ignored_branch(self) -> None:
        """
        [COMMON-SECRET:T01-05-04] _load_json: 破損JSON→復旧save失敗でも {} を返す
        """
        p = self.base / "broken.json"
        p.write_text("{ invalid json", encoding="utf-8")

        # 復旧保存を試みるが _save_json が落ちても {} を返し、例外は外に出さない
        with patch.object(self.ss, "_save_json", side_effect=RuntimeError("boom")):
            got = self.ss._load_json(p)
        self.assertEqual(got, {})

    def test_05_save_json_cleanup_unlink_raises_is_ignored_branch(self) -> None:
        """
        [COMMON-SECRET:T01-05-05] _save_json: cleanup unlink 失敗を握りつぶす
        """
        p = self.base / "out.json"

        # os.replace を失敗させて except に入り、tmp の os.remove が呼ばれるパスを作る。
        # その os.remove が OSError を投げても握りつぶされることを確認（例外が外に出ない）。
        def _fake_replace(_src: str, _dst: str) -> None:
            raise OSError("replace failed")

        with patch("os.replace", side_effect=_fake_replace), patch("os.path.exists", return_value=True), patch(
            "os.remove", side_effect=OSError("unlink failed")
        ):
            # 例外が外に出なければOK（副作用の成否はここでは問わない）
            self.ss._save_json(p, {"a": 1})


def _suite() -> unittest.TestSuite:
    loader = unittest.TestLoader()
    return loader.loadTestsFromTestCase(SecretStoreImplMiscTest)


if __name__ == "__main__":
    suite = _suite()
    mapping = {
        "SecretStoreImplMiscTest.test_01_backend_name_matches_impl": (
            "COMMON-SECRET:T01-05-01",
            "backend_name が実装名を返す",
        ),
        "SecretStoreImplMiscTest.test_02_dec_empty_raises_value_error_branch": (
            "COMMON-SECRET:T01-05-02",
            "_dec('') は ValueError",
        ),
        "SecretStoreImplMiscTest.test_03_load_json_missing_path_returns_empty_branch": (
            "COMMON-SECRET:T01-05-03",
            "_load_json: パス無し -> {}",
        ),
        "SecretStoreImplMiscTest.test_04_load_json_recovery_save_fails_is_ignored_branch": (
            "COMMON-SECRET:T01-05-04",
            "_load_json: 破損JSON→復旧save失敗でも {} を返す",
        ),
        "SecretStoreImplMiscTest.test_05_save_json_cleanup_unlink_raises_is_ignored_branch": (
            "COMMON-SECRET:T01-05-05",
            "_save_json: cleanup unlink 失敗を握りつぶす",
        ),
    }
    run_unittest_suite("COMMON-SECRET:T01-05 (impl) common/secret/store", suite, mapping)
