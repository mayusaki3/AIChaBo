# -*- coding: utf-8 -*-
"""
COMMON-SESSION:T01 : user_session_manager

対象: common.session.user_session_manager

目的:
- UserSessionManager の公的API（get/set/has/clear）を Discord 非依存で検証する
- 保存先（PATH: ~/.aichabo/usersessions.json）をテスト中のみ一時パスへ差し替え、安全に実行する
- set_session 時に deep に api_key が除去されること
- 必須: chat.provider / chat.model（空白のみ不可）

テスト番号:
- COMMON-SESSION:T01-01-01 ... （T01=USM, 01=テストコード, 01..=ケース）

実行:
- python -m tests.common.session.T01_UserSession_01_user_session_test
"""

import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, Tuple

from tests._report import run_unittest_suite


class UserSessionManagerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from common.session import user_session_manager as usm_mod  # type: ignore
        cls.usm_mod = usm_mod

        # 退避
        cls._orig_path = getattr(usm_mod, "PATH", None)
        cls._orig_singleton = getattr(usm_mod, "user_session_manager", None)

        # テスト用PATHへ差し替え
        cls._tmpdir = Path(tempfile.mkdtemp(prefix="aichabo_usm_"))
        cls._test_path = cls._tmpdir / "usersessions.json"
        cls._test_path.write_text("{}", encoding="utf-8")

        usm_mod.PATH = cls._test_path
        usm_mod.user_session_manager = usm_mod.UserSessionManager()

    @classmethod
    def tearDownClass(cls):
        # 復元
        try:
            cls.usm_mod.PATH = cls._orig_path
        except Exception:
            pass
        try:
            cls.usm_mod.user_session_manager = cls._orig_singleton
        except Exception:
            pass

        # 一時ディレクトリ削除（失敗しても握り潰す）
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

    # [COMMON-SESSION:T01-01-01] guard(None) -> None
    def test_01_guard_none_user_id_returns_none(self):
        got = self.usm_mod.user_session_manager.get_session(None)  # type: ignore[arg-type]
        self.assertIsNone(got)

    # [COMMON-SESSION:T01-01-02] unregistered -> None
    def test_02_get_unregistered_returns_none(self):
        self.assertIsNone(self.usm_mod.user_session_manager.get_session(987654321))

    # [COMMON-SESSION:T01-01-03] set/get minimal & strip api_key（深い階層も除去）
    def test_03_set_get_minimal_and_strip_api_key(self):
        uid = 1001
        payload: Dict[str, Any] = {
            "chat": {"provider": " openai ", "model": " gpt-4o-mini "},  # strip()される
            "api_key": "REMOVE_ME",
            "nested": {"api_key": "REMOVE_ME_TOO", "arr": [{"api_key": "X"}]},
        }

        self.usm_mod.user_session_manager.set_session(uid, payload)
        self.assertTrue(self.usm_mod.user_session_manager.has_session(uid))

        got = self.usm_mod.user_session_manager.get_session(uid)
        self.assertIsInstance(got, dict)

        # chat.provider/model が trim 済みで保存される
        chat = got.get("chat") or {}
        self.assertEqual(chat.get("provider"), "openai")
        self.assertEqual(chat.get("model"), "gpt-4o-mini")

        # deep に api_key が削除されている
        self.assertNotIn("api_key", got)
        self.assertNotIn("api_key", (got.get("nested") or {}))
        self.assertTrue(all("api_key" not in d for d in (got.get("nested") or {}).get("arr", [])))

        # user_id が str で保存される
        self.assertEqual(got.get("user_id"), str(uid))

    # [COMMON-SESSION:T01-01-04] clear_session removes entry
    def test_04_clear_session(self):
        uid = 1002
        self.usm_mod.user_session_manager.set_session(uid, {"chat": {"provider": "openai", "model": "gpt"}})
        self.assertTrue(self.usm_mod.user_session_manager.has_session(uid))
        self.usm_mod.user_session_manager.clear_session(uid)
        self.assertFalse(self.usm_mod.user_session_manager.has_session(uid))
        self.assertIsNone(self.usm_mod.user_session_manager.get_session(uid))

    # [COMMON-SESSION:T01-01-05] required: chat.provider/chat.model missing -> ValueError
    def test_05_requires_chat_provider_model(self):
        uid = 1003
        with self.assertRaises(ValueError) as cm:
            self.usm_mod.user_session_manager.set_session(uid, {"provider": "openai", "model": "gpt"})
        self.assertIn("chat.provider and chat.model are required", str(cm.exception))

    # [COMMON-SESSION:T01-01-06] chat must be dict -> ValueError
    def test_06_chat_must_be_dict(self):
        uid = 1004
        with self.assertRaises(ValueError) as cm:
            self.usm_mod.user_session_manager.set_session(uid, {"chat": "x"})  # type: ignore[arg-type]
        self.assertIn("chat must be a dict", str(cm.exception))

    # [COMMON-SESSION:T01-01-07] required: blank provider/model -> ValueError
    def test_07_requires_non_blank_provider_model(self):
        uid = 1005
        with self.assertRaises(ValueError):
            self.usm_mod.user_session_manager.set_session(uid, {"chat": {"provider": "   ", "model": "gpt"}})
        with self.assertRaises(ValueError):
            self.usm_mod.user_session_manager.set_session(uid, {"chat": {"provider": "openai", "model": "   "}})

    # [COMMON-SESSION:T01-01-08] 起動時ロード例外 → 復旧
    def test_08_init_load_exception_recovers_empty(self):
        import importlib
        from unittest.mock import patch

        usm_mod = self.usm_mod

        with patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.read_text", side_effect=Exception("boom")), \
             patch("pathlib.Path.write_text") as mock_write:

            # reload で __init__ のロード処理を踏ませる
            reloaded = importlib.reload(usm_mod)

            mgr = reloaded.UserSessionManager()

            self.assertEqual(mgr.sessions, {})
            mock_write.assert_called()  # "{}" で復旧

    # [COMMON-SESSION:T01-01-09] 起動時ロード: PATH.exists() == False → そのまま空で起動
    def test_09_init_path_not_exists_keeps_empty(self):
        import importlib
        from unittest.mock import patch

        usm_mod = self.usm_mod

        with patch("pathlib.Path.exists", return_value=False):
            reloaded = importlib.reload(usm_mod)
            mgr = reloaded.UserSessionManager()
            self.assertEqual(mgr.sessions, {})


if __name__ == "__main__":
    mapping: Dict[str, Tuple[str, str]] = {
        "test_01_guard_none_user_id_returns_none": ("COMMON-SESSION:T01-01-01", "guard(None) -> None"),
        "test_02_get_unregistered_returns_none": ("COMMON-SESSION:T01-01-02", "unregistered -> None"),
        "test_03_set_get_minimal_and_strip_api_key": ("COMMON-SESSION:T01-01-03", "set/get minimal & strip api_key"),
        "test_04_clear_session": ("COMMON-SESSION:T01-01-04", "clear_session removes entry"),
        "test_05_requires_chat_provider_model": ("COMMON-SESSION:T01-01-05", "requires chat.provider/chat.model -> ValueError"),
        "test_06_chat_must_be_dict": ("COMMON-SESSION:T01-01-06", "chat must be a dict -> ValueError"),
        "test_07_requires_non_blank_provider_model": ("COMMON-SESSION:T01-01-07", "blank provider/model -> ValueError"),
        "test_08_init_load_exception_recovers_empty": ("COMMON-SESSION:T01-01-08", "起動時ロード例外 → 復旧"),
        "test_09_init_path_not_exists_keeps_empty": ("COMMON-SESSION:T01-01-09", "起動時ロード: PATH.exists()==False → 空で起動"),
    }
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(UserSessionManagerTest)
    run_unittest_suite("COMMON-SESSION:T01 common/session/user_session_manager", suite, mapping)
