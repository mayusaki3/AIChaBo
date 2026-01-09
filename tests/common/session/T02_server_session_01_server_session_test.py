# tests/common/session/T02_server_session_01_server_session_test.py
# -*- coding: utf-8 -*-
"""
COMMON-SESSION:T02-01 : ServerSession 管理（SSM）仕様テスト

対象: common/session/server_session_manager.py

目的:
- ServerSessionManager の公的APIを Discord 非依存で検証する
  - 共有認証設定（set/get/clear）
  - システムオプション（set/get/clear/all）
- 保存先（PATH_SHARED / PATH_OPTS）をテスト中のみ一時パスへ差し替え、安全に実行する

注意:
- _report.py の仕様に合わせ、mapping は test_xxx をキーにする
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, Tuple

from tests._report import run_unittest_suite


class ServerSessionManagerSpecTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from common.session import server_session_manager as ssm_mod  # type: ignore

        cls.ssm_mod = ssm_mod

        # 退避
        cls._orig_shared = getattr(ssm_mod, "PATH_SHARED", None)
        cls._orig_opts = getattr(ssm_mod, "PATH_OPTS", None)
        cls._orig_singleton = getattr(ssm_mod, "server_session_manager", None)

        # テスト用 PATH へ差し替え
        cls._tmpdir = Path(tempfile.mkdtemp(prefix="aichabo_ssm_"))
        cls._test_shared = cls._tmpdir / "servershared.json"
        cls._test_opts = cls._tmpdir / "serveropts.json"
        cls._test_shared.write_text("{}", encoding="utf-8")
        cls._test_opts.write_text("{}", encoding="utf-8")

        ssm_mod.PATH_SHARED = cls._test_shared
        ssm_mod.PATH_OPTS = cls._test_opts

        # シングルトンを作り直す
        ssm_mod.server_session_manager = ssm_mod.ServerSessionManager()

    @classmethod
    def tearDownClass(cls) -> None:
        # 復元
        try:
            cls.ssm_mod.PATH_SHARED = cls._orig_shared
        except Exception:
            pass
        try:
            cls.ssm_mod.PATH_OPTS = cls._orig_opts
        except Exception:
            pass
        try:
            cls.ssm_mod.server_session_manager = cls._orig_singleton
        except Exception:
            pass

        # temp 削除（失敗しても握り潰す）
        try:
            if cls._tmpdir.exists():
                for p in cls._tmpdir.glob("*"):
                    try:
                        p.unlink()
                    except Exception:
                        pass
                cls._tmpdir.rmdir()
        except Exception:
            pass

    # [COMMON-SESSION:T02-01-01] guard(None) | get_shared_auth_config(None) は {}
    def test_01_get_shared_auth_config_guard(self) -> None:
        got = self.ssm_mod.server_session_manager.get_shared_auth_config(None)  # type: ignore[arg-type]
        self.assertEqual(got, {})

    # [COMMON-SESSION:T02-01-02] 未登録 | 未登録 server_id の get_shared_auth_config は {}
    def test_02_get_shared_auth_config_unregistered(self) -> None:
        self.assertEqual(self.ssm_mod.server_session_manager.get_shared_auth_config(999999), {})

    # [COMMON-SESSION:T02-01-03] set/get（api_key除去 + provider/model trim）
    def test_03_set_get_shared_auth_config_and_strip_api_key(self) -> None:
        gid = 2001
        payload: Dict[str, Any] = {
            "chat": {"provider": " openai ", "model": " gpt-4o-mini "},
            "api_key": "REMOVE_ME",
            "nested": {"api_key": "REMOVE_ME_TOO", "arr": [{"api_key": "X"}]},
        }
        self.ssm_mod.server_session_manager.set_shared_auth_config(gid, payload)

        got = self.ssm_mod.server_session_manager.get_shared_auth_config(gid)
        self.assertIsInstance(got, dict)

        chat = got.get("chat") or {}
        self.assertEqual(chat.get("provider"), "openai")
        self.assertEqual(chat.get("model"), "gpt-4o-mini")

        # deep に api_key が削除されている（dict/list 再帰）
        self.assertNotIn("api_key", got)
        self.assertNotIn("api_key", (got.get("nested") or {}))
        self.assertTrue(all("api_key" not in d for d in (got.get("nested") or {}).get("arr", [])))

    # [COMMON-SESSION:T02-01-04] clear_shared_auth_config | clear 後は {}
    def test_04_clear_shared_auth_config(self) -> None:
        gid = 2002
        self.ssm_mod.server_session_manager.set_shared_auth_config(
            gid, {"chat": {"provider": "openai", "model": "gpt"}}
        )
        self.assertNotEqual(self.ssm_mod.server_session_manager.get_shared_auth_config(gid), {})

        self.ssm_mod.server_session_manager.clear_shared_auth_config(gid)
        self.assertEqual(self.ssm_mod.server_session_manager.get_shared_auth_config(gid), {})

    # [COMMON-SESSION:T02-01-05] 必須不足は ValueError（chat.provider/chat.model）
    def test_05_set_shared_auth_config_requires_chat_provider_model(self) -> None:
        gid = 2003
        with self.assertRaises(ValueError) as cm:
            self.ssm_mod.server_session_manager.set_shared_auth_config(gid, {"provider": "openai", "model": "gpt"})
        self.assertIn("chat.provider and chat.model are required", str(cm.exception))

    # [COMMON-SESSION:T02-01-06] chat 型不正は ValueError("chat must be a dict")
    def test_06_set_shared_auth_config_chat_must_be_dict(self) -> None:
        gid = 2004
        with self.assertRaises(ValueError) as cm:
            self.ssm_mod.server_session_manager.set_shared_auth_config(gid, {"chat": "x"})  # type: ignore[arg-type]
        self.assertIn("chat must be a dict", str(cm.exception))

    # [COMMON-SESSION:T02-01-07] option set/get/clear/all
    def test_07_set_get_clear_option(self) -> None:
        gid = 2005

        # default が効く
        self.assertIsNone(self.ssm_mod.server_session_manager.get_option(gid, "printmsg"))
        self.assertEqual(self.ssm_mod.server_session_manager.get_option(gid, "printmsg", default=False), False)

        # set は key を lower に正規化し、bool化して保存
        self.ssm_mod.server_session_manager.set_option(gid, "PrintMsg", True)
        self.assertEqual(self.ssm_mod.server_session_manager.get_option(gid, "printmsg"), True)

        # all_options
        self.assertEqual(self.ssm_mod.server_session_manager.all_options(gid), {"printmsg": True})

        # clear
        self.ssm_mod.server_session_manager.clear_option(gid, "PRINTMSG")
        self.assertEqual(self.ssm_mod.server_session_manager.get_option(gid, "printmsg"), None)
        self.assertEqual(self.ssm_mod.server_session_manager.all_options(gid), {})


# test_xxx -> (番号, 説明)
mapping: Dict[str, Tuple[str, str]] = {
    "test_01_get_shared_auth_config_guard": ("COMMON-SESSION:T02-01-01", "guard(None) -> {}"),
    "test_02_get_shared_auth_config_unregistered": ("COMMON-SESSION:T02-01-02", "unregistered -> {}"),
    "test_03_set_get_shared_auth_config_and_strip_api_key": ("COMMON-SESSION:T02-01-03", "set/get shared auth & strip api_key"),
    "test_04_clear_shared_auth_config": ("COMMON-SESSION:T02-01-04", "clear_shared_auth_config -> {}"),
    "test_05_set_shared_auth_config_requires_chat_provider_model": ("COMMON-SESSION:T02-01-05", "requires chat.provider/chat.model -> ValueError"),
    "test_06_set_shared_auth_config_chat_must_be_dict": ("COMMON-SESSION:T02-01-06", "chat must be a dict -> ValueError"),
    "test_07_set_get_clear_option": ("COMMON-SESSION:T02-01-07", "option set/get/clear/all"),
}

if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ServerSessionManagerSpecTest)
    run_unittest_suite("COMMON-SESSION:T02-01 common/session/server_session_manager", suite, mapping)
