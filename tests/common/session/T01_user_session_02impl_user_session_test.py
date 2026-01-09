# tests/common/session/T01_user_session_02impl_user_session_test.py
# -*- coding: utf-8 -*-
"""
COMMON-SESSION:T01-02 : UserSession 管理（USM）impl/branch テスト（カバレッジ目的）

対象: common/session/user_session_manager.py
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Dict, Tuple

from tests._report import run_unittest_suite


class UserSessionManagerImplTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from common.session import user_session_manager as usm_mod  # type: ignore

        cls.usm_mod = usm_mod

        cls._orig_path = getattr(usm_mod, "PATH", None)
        cls._orig_singleton = getattr(usm_mod, "user_session_manager", None)

        cls._tmpdir = Path(tempfile.mkdtemp(prefix="aichabo_usm_impl_"))
        cls._test_path = cls._tmpdir / "usersessions.json"
        cls._test_path.write_text("{}", encoding="utf-8")

        usm_mod.PATH = cls._test_path
        usm_mod.user_session_manager = usm_mod.UserSessionManager()

    @classmethod
    def tearDownClass(cls) -> None:
        try:
            cls.usm_mod.PATH = cls._orig_path
        except Exception:
            pass
        try:
            cls.usm_mod.user_session_manager = cls._orig_singleton
        except Exception:
            pass

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

    # [COMMON-SESSION:T01-02-01] has_session True/False
    def test_01_has_session_true_false(self) -> None:
        mgr = self.usm_mod.user_session_manager
        self.assertFalse(mgr.has_session(1))
        mgr.set_session(1, {"chat": {"provider": "openai", "model": "gpt"}})
        self.assertTrue(mgr.has_session(1))

    # [COMMON-SESSION:T01-02-02] clear_session no-op（未登録でも落ちない）
    def test_02_clear_session_noop_when_missing(self) -> None:
        mgr = self.usm_mod.user_session_manager
        mgr.clear_session(999999)  # no exception
        self.assertIsNone(mgr.get_session(999999))

    # [COMMON-SESSION:T01-02-03] get_session は deepcopy（参照が外部に漏れない）
    def test_03_get_session_returns_deepcopy(self) -> None:
        mgr = self.usm_mod.user_session_manager
        mgr.set_session(2, {"chat": {"provider": "openai", "model": "gpt"}, "nested": {"x": 1}})
        got1 = mgr.get_session(2)
        self.assertIsInstance(got1, dict)

        # 取得結果を改変しても内部に影響しない
        got1["nested"]["x"] = 999  # type: ignore[index]
        got2 = mgr.get_session(2)
        self.assertEqual((got2.get("nested") or {}).get("x"), 1)


mapping: Dict[str, Tuple[str, str]] = {
    "test_01_has_session_true_false": ("COMMON-SESSION:T01-02-01", "has_session: False->True"),
    "test_02_clear_session_noop_when_missing": ("COMMON-SESSION:T01-02-02", "clear_session: missing no-op"),
    "test_03_get_session_returns_deepcopy": ("COMMON-SESSION:T01-02-03", "get_session: deepcopy を返す"),
}

if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(UserSessionManagerImplTest)
    run_unittest_suite("COMMON-SESSION:T01-02 (impl) common/session/user_session_manager", suite, mapping)
