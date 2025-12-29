# -*- coding: utf-8 -*-
"""
COMMON-SESSION:T02 : server_session_manager (branch/coverage)

対象: common.session.server_session_manager

目的:
- T02-01 で踏めない分岐（起動時ロード例外復旧・exists False・strip再帰・clear_option空削除など）を網羅し、
  server_session_manager.py を 100% にする。

テスト番号:
- COMMON-SESSION:T02-02-01 ... （T02=SSM, 02=テストコード, 01..=ケース）

実行:
- python -m tests.common.session.T02_ServerSession_02_server_session_branch_test
"""

import importlib
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, Tuple
from unittest.mock import patch

from tests._report import run_unittest_suite


class ServerSessionManagerBranchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from common.session import server_session_manager as ssm_mod  # type: ignore
        cls.ssm_mod = ssm_mod

        # 退避
        cls._orig_shared = getattr(ssm_mod, "PATH_SHARED", None)
        cls._orig_opts = getattr(ssm_mod, "PATH_OPTS", None)
        cls._orig_singleton = getattr(ssm_mod, "server_session_manager", None)

        # テスト用PATH
        cls._tmpdir = Path(tempfile.mkdtemp(prefix="aichabo_ssm_branch_"))
        cls._test_shared = cls._tmpdir / "servershared.json"
        cls._test_opts = cls._tmpdir / "serveropts.json"
        cls._test_shared.write_text("{}", encoding="utf-8")
        cls._test_opts.write_text("{}", encoding="utf-8")

        ssm_mod.PATH_SHARED = cls._test_shared
        ssm_mod.PATH_OPTS = cls._test_opts
        ssm_mod.server_session_manager = ssm_mod.ServerSessionManager()

    @classmethod
    def tearDownClass(cls):
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

        # tmp削除（失敗しても握り潰す）
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

    # [COMMON-SESSION:T02-02-01] 起動時ロード: PATH_SHARED.exists()==False / PATH_OPTS.exists()==False
    def test_01_init_paths_not_exists_keeps_empty(self):
        m = self.ssm_mod
        with patch("pathlib.Path.exists", return_value=False):
            reloaded = importlib.reload(m)
            mgr = reloaded.ServerSessionManager()
            self.assertEqual(mgr.get_shared_auth_config(1), {})
            self.assertEqual(mgr.all_options(1), {})

    # [COMMON-SESSION:T02-02-02] 起動時ロード: shared read_text 例外 → {} & write_text("{}")
    def test_02_init_shared_load_exception_recovers(self):
        m = self.ssm_mod
        with patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.read_text", side_effect=Exception("boom")), \
             patch("pathlib.Path.write_text") as mock_write:
            reloaded = importlib.reload(m)
            mgr = reloaded.ServerSessionManager()
            self.assertEqual(mgr.get_shared_auth_config(1), {})
            mock_write.assert_called()

    # [COMMON-SESSION:T02-02-03] 起動時ロード: opts read_text 例外 → {} & write_text("{}")
    def test_03_init_opts_load_exception_recovers(self):
        m = self.ssm_mod

        # shared は正常、opts の read_text だけ例外にしたいので side_effect を分岐させる
        def _read_text_side_effect(self_path: Path, *args, **kwargs):
            # serveropts.json の読み取りだけ落とす
            if str(self_path).endswith("serveropts.json"):
                raise Exception("boom-opts")
            return "{}"

        with patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.read_text", new=_read_text_side_effect), \
             patch("pathlib.Path.write_text") as mock_write:
            reloaded = importlib.reload(m)
            mgr = reloaded.ServerSessionManager()
            self.assertEqual(mgr.all_options(1), {})
            mock_write.assert_called()

    # [COMMON-SESSION:T02-02-04] _strip_api_keys: dict/list/other の再帰除去
    def test_04_strip_api_keys_recursive(self):
        mgr = self.ssm_mod.server_session_manager
        src: Dict[str, Any] = {
            "api_key": "REMOVE",
            "chat": {"provider": "openai", "model": "gpt"},
            "nested": {"api_key": "X", "arr": [{"api_key": "Y", "v": 1}, 2, "s"]},
        }
        out = mgr._strip_api_keys(src)  # type: ignore[attr-defined]
        self.assertNotIn("api_key", out)
        self.assertNotIn("api_key", out.get("nested", {}))
        arr = out.get("nested", {}).get("arr", [])
        self.assertIsInstance(arr, list)
        self.assertNotIn("api_key", arr[0])

    # [COMMON-SESSION:T02-02-05] set_shared_auth_config: chat が dict 以外 → ValueError("chat must be a dict")
    def test_05_set_shared_auth_config_chat_must_be_dict(self):
        mgr = self.ssm_mod.server_session_manager
        with self.assertRaises(ValueError) as cm:
            mgr.set_shared_auth_config(1, {"chat": "x"})  # type: ignore[arg-type]
        self.assertIn("chat must be a dict", str(cm.exception))

    # [COMMON-SESSION:T02-02-06] set_shared_auth_config: provider/model trim が保存される
    def test_06_set_shared_auth_config_trims(self):
        mgr = self.ssm_mod.server_session_manager
        mgr.set_shared_auth_config(2, {"chat": {"provider": " openai ", "model": " gpt-4o "}})
        got = mgr.get_shared_auth_config(2)
        self.assertEqual((got.get("chat") or {}).get("provider"), "openai")
        self.assertEqual((got.get("chat") or {}).get("model"), "gpt-4o")

    # [COMMON-SESSION:T02-02-07] clear_option: 最後のキー削除で sid 自体が system_options から消える
    def test_07_clear_option_removes_sid_when_empty(self):
        mgr = self.ssm_mod.server_session_manager
        sid = 9999
        mgr.set_option(sid, "printmsg", True)
        self.assertEqual(mgr.all_options(sid), {"printmsg": True})
        mgr.clear_option(sid, "printmsg")
        self.assertEqual(mgr.all_options(sid), {})
        # sid が消えていること（実装は空なら pop）
        self.assertNotIn(str(sid), mgr.system_options)  # type: ignore[attr-defined]

    # [COMMON-SESSION:T02-02-08] clear_option: sid 未登録でも例外なく終了（no-op 分岐）
    def test_08_clear_option_noop_when_sid_missing(self):
        mgr = self.ssm_mod.server_session_manager
        # 未登録 sid に対して clear しても落ちない
        mgr.clear_option(123456, "printmsg")
        self.assertEqual(mgr.all_options(123456), {})

    # [COMMON-SESSION:T02-02-09] clear_option: key 未登録でも例外なく終了（no-op 分岐）
    def test_09_clear_option_noop_when_key_missing(self):
        mgr = self.ssm_mod.server_session_manager
        sid = 2222
        mgr.set_option(sid, "printmsg", True)
        # 存在しないキーを clear しても no-op
        mgr.clear_option(sid, "no_such_key")
        self.assertEqual(mgr.all_options(sid), {"printmsg": True})


if __name__ == "__main__":
    mapping: Dict[str, Tuple[str, str]] = {
        "test_01_init_paths_not_exists_keeps_empty": ("COMMON-SESSION:T02-02-01", "起動時ロード: exists False（shared/opts）"),
        "test_02_init_shared_load_exception_recovers": ("COMMON-SESSION:T02-02-02", "起動時ロード: shared read_text例外 → 復旧"),
        "test_03_init_opts_load_exception_recovers": ("COMMON-SESSION:T02-02-03", "起動時ロード: opts read_text例外 → 復旧"),
        "test_04_strip_api_keys_recursive": ("COMMON-SESSION:T02-02-04", "_strip_api_keys 再帰除去（dict/list/other）"),
        "test_05_set_shared_auth_config_chat_must_be_dict": ("COMMON-SESSION:T02-02-05", "set_shared_auth_config: chat型不正 → ValueError"),
        "test_06_set_shared_auth_config_trims": ("COMMON-SESSION:T02-02-06", "set_shared_auth_config: provider/model trim を保存"),
        "test_07_clear_option_removes_sid_when_empty": ("COMMON-SESSION:T02-02-07", "clear_option: 空なら sid を削除"),
        "test_08_clear_option_noop_when_sid_missing": ("COMMON-SESSION:T02-02-08", "clear_option: sid 未登録 no-op"),
        "test_09_clear_option_noop_when_key_missing": ("COMMON-SESSION:T02-02-09", "clear_option: key 未登録 no-op"),
    }
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ServerSessionManagerBranchTest)
    run_unittest_suite("COMMON-SESSION:T02-02 common/session/server_session_manager branch", suite, mapping)
