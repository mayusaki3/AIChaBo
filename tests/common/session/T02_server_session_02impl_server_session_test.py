# tests/common/session/T02_server_session_02impl_server_session_test.py
# -*- coding: utf-8 -*-
"""
COMMON-SESSION:T02-02 : ServerSession 管理（SSM）impl/branch テスト（カバレッジ目的）

対象: common/session/server_session_manager.py

目的:
- __init__ の exists(False) 分岐
- __init__ の read 例外復旧分岐
- clear_option の分岐（sid未登録 / key未登録 / sid空で削除 / sid空でない）
"""

from __future__ import annotations

import os
import unittest
from pathlib import Path
from typing import Dict, Tuple
from unittest.mock import patch

from tests._report import run_unittest_suite


class ServerSessionManagerImplTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from common.session import server_session_manager as ssm_mod  # type: ignore

        cls.ssm_mod = ssm_mod

        # 退避
        cls._orig_shared = getattr(ssm_mod, "PATH_SHARED", None)
        cls._orig_opts = getattr(ssm_mod, "PATH_OPTS", None)
        cls._orig_singleton = getattr(ssm_mod, "server_session_manager", None)

        # テスト用 PATH（実ファイルを使わない）
        tmp = Path(os.getcwd()) / ".tmp_test_ssm_impl"
        tmp.mkdir(parents=True, exist_ok=True)
        cls._tmpdir = tmp
        cls._test_shared = tmp / "servershared.json"
        cls._test_opts = tmp / "serveropts.json"
        cls._test_shared.write_text("{}", encoding="utf-8")
        cls._test_opts.write_text("{}", encoding="utf-8")

        ssm_mod.PATH_SHARED = cls._test_shared
        ssm_mod.PATH_OPTS = cls._test_opts
        ssm_mod.server_session_manager = ssm_mod.ServerSessionManager()

    @classmethod
    def tearDownClass(cls) -> None:
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

        # tmp 削除（失敗しても握り潰す）
        try:
            for p in cls._tmpdir.glob("*"):
                try:
                    p.unlink()
                except Exception:
                    pass
            try:
                cls._tmpdir.rmdir()
            except Exception:
                pass
        except Exception:
            pass

    # [COMMON-SESSION:T02-02-01] init: exists False（shared/opts）→ 読み込みしない
    def test_01_init_paths_not_exists_keeps_empty(self) -> None:
        ssm_mod = self.ssm_mod

        with patch("pathlib.Path.exists", return_value=False), \
             patch("pathlib.Path.read_text", side_effect=AssertionError("read_text must not be called")), \
             patch("pathlib.Path.write_text", side_effect=AssertionError("write_text must not be called")):
            mgr = ssm_mod.ServerSessionManager()
            self.assertEqual(mgr.get_shared_auth_config(1), {})
            self.assertEqual(mgr.all_options(1), {})

    # [COMMON-SESSION:T02-02-02] init: shared read 例外 → {} 復旧 + write
    def test_02_init_shared_load_exception_recovers_empty(self) -> None:
        ssm_mod = self.ssm_mod

        with patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.read_text", side_effect=Exception("boom")), \
             patch("pathlib.Path.write_text") as mock_write:
            mgr = ssm_mod.ServerSessionManager()
            self.assertEqual(mgr.get_shared_auth_config(1), {})
            mock_write.assert_called()

    # [COMMON-SESSION:T02-02-03] init: opts read 例外 → {} 復旧 + write
    def test_03_init_opts_load_exception_recovers_empty(self) -> None:
        ssm_mod = self.ssm_mod

        def _read_text_side_effect(self_path: Path, *args, **kwargs):
            if str(self_path).endswith("serveropts.json"):
                raise Exception("boom-opts")
            return "{}"

        with patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.read_text", new=_read_text_side_effect), \
             patch("pathlib.Path.write_text") as mock_write:
            mgr = ssm_mod.ServerSessionManager()
            self.assertEqual(mgr.all_options(1), {})
            mock_write.assert_called()

    # [COMMON-SESSION:T02-02-04] clear_option: sid 未登録 no-op（102->exit）
    def test_04_clear_option_noop_when_sid_missing(self) -> None:
        mgr = self.ssm_mod.server_session_manager
        mgr.clear_option(123456, "printmsg")  # no exception
        self.assertEqual(mgr.all_options(123456), {})

    # [COMMON-SESSION:T02-02-05] clear_option: key 未登録 no-op（sidは残る）
    def test_05_clear_option_noop_when_key_missing(self) -> None:
        mgr = self.ssm_mod.server_session_manager
        sid = 2222
        mgr.set_option(sid, "printmsg", True)
        mgr.clear_option(sid, "no_such_key")
        self.assertEqual(mgr.all_options(sid), {"printmsg": True})

    # [COMMON-SESSION:T02-02-06] clear_option: 最後のkey削除でsid bucketも削除（104 true）
    def test_06_clear_option_removes_bucket_when_empty(self) -> None:
        mgr = self.ssm_mod.server_session_manager
        sid = 9999
        mgr.set_option(sid, "printmsg", True)
        self.assertEqual(mgr.all_options(sid), {"printmsg": True})

        mgr.clear_option(sid, "printmsg")
        self.assertEqual(mgr.all_options(sid), {})
        self.assertNotIn(str(sid), mgr.system_options)

    # [COMMON-SESSION:T02-02-07] clear_option: sid bucket が空でない分岐（104 false）
    def test_07_clear_option_keeps_bucket_when_not_empty(self) -> None:
        mgr = self.ssm_mod.server_session_manager
        sid = 7777
        mgr.set_option(sid, "printmsg", True)
        mgr.set_option(sid, "other", True)
        self.assertEqual(mgr.all_options(sid), {"printmsg": True, "other": True})

        mgr.clear_option(sid, "printmsg")
        self.assertEqual(mgr.all_options(sid), {"other": True})
        self.assertIn(str(sid), mgr.system_options)


mapping: Dict[str, Tuple[str, str]] = {
    "test_01_init_paths_not_exists_keeps_empty": ("COMMON-SESSION:T02-02-01", "init: exists False（shared/opts）"),
    "test_02_init_shared_load_exception_recovers_empty": ("COMMON-SESSION:T02-02-02", "init(shared): read例外 → {} 復旧 + write"),
    "test_03_init_opts_load_exception_recovers_empty": ("COMMON-SESSION:T02-02-03", "init(opts): read例外 → {} 復旧 + write"),
    "test_04_clear_option_noop_when_sid_missing": ("COMMON-SESSION:T02-02-04", "clear_option: sid 未登録 no-op"),
    "test_05_clear_option_noop_when_key_missing": ("COMMON-SESSION:T02-02-05", "clear_option: key 未登録 no-op"),
    "test_06_clear_option_removes_bucket_when_empty": ("COMMON-SESSION:T02-02-06", "clear_option: 最後のkey削除でbucketも削除"),
    "test_07_clear_option_keeps_bucket_when_not_empty": ("COMMON-SESSION:T02-02-07", "clear_option: bucket が空でない分岐"),
}

if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ServerSessionManagerImplTest)
    run_unittest_suite("COMMON-SESSION:T02-02 (impl) common/session/server_session_manager", suite, mapping)
