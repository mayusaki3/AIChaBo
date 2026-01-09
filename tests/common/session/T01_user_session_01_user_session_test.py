# tests/common/session/T01_user_session_01_user_session_test.py
# -*- coding: utf-8 -*-
"""
COMMON-SESSION:T01-01 : UserSession 管理（USM）仕様テスト

対象: common/session/user_session_manager.py

方針:
- 保存先 PATH（~/.aichabo/usersessions.json）をテスト中のみ一時パスへ差し替え、安全に実行する
- _report.py の仕様に合わせ、mapping は test_xxx をキーにする
"""

from __future__ import annotations

import importlib
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, Tuple
from unittest.mock import patch

from tests._report import run_unittest_suite


class UserSessionManagerSpecTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        # モジュールを保持（PATH / singleton を差し替えるため）
        from common.session import user_session_manager as usm_mod  # type: ignore

        cls.usm_mod = usm_mod

        # 退避
        cls._orig_path = getattr(usm_mod, "PATH", None)
        cls._orig_singleton = getattr(usm_mod, "user_session_manager", None)

        # テスト用 PATH へ差し替え
        cls._tmpdir = Path(tempfile.mkdtemp(prefix="aichabo_usm_"))
        cls._test_path = cls._tmpdir / "usersessions.json"
        cls._test_path.write_text("{}", encoding="utf-8")

        usm_mod.PATH = cls._test_path
        usm_mod.user_session_manager = usm_mod.UserSessionManager()

    @classmethod
    def tearDownClass(cls) -> None:
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

    # [COMMON-SESSION:T01-01-01] guard(None) | get_session(None) は None
    def test_01_guard_none_user_id_returns_none(self) -> None:
        got = self.usm_mod.user_session_manager.get_session(None)  # type: ignore[arg-type]
        self.assertIsNone(got)

    # [COMMON-SESSION:T01-01-02] 未登録 | 未登録 user_id の get_session は None
    def test_02_get_unregistered_returns_none(self) -> None:
        self.assertIsNone(self.usm_mod.user_session_manager.get_session(987654321))

    # [COMMON-SESSION:T01-01-03] set/get + api_key 非保持（深い階層も除去）
    def test_03_set_get_minimal_and_strip_api_key(self) -> None:
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

    # [COMMON-SESSION:T01-01-04] clear_session | clear_session 後に get_session は None
    def test_04_clear_session(self) -> None:
        uid = 1002
        self.usm_mod.user_session_manager.set_session(uid, {"chat": {"provider": "openai", "model": "gpt"}})
        self.assertTrue(self.usm_mod.user_session_manager.has_session(uid))

        self.usm_mod.user_session_manager.clear_session(uid)
        self.assertFalse(self.usm_mod.user_session_manager.has_session(uid))
        self.assertIsNone(self.usm_mod.user_session_manager.get_session(uid))

    # [COMMON-SESSION:T01-01-05] 必須不足は ValueError（chat.provider/chat.model）
    def test_05_requires_chat_provider_model(self) -> None:
        uid = 1003
        with self.assertRaises(ValueError) as cm:
            self.usm_mod.user_session_manager.set_session(uid, {"provider": "openai", "model": "gpt"})
        self.assertIn("chat.provider and chat.model are required", str(cm.exception))

    # [COMMON-SESSION:T01-01-06] chat 型不正は ValueError("chat must be a dict")
    def test_06_chat_must_be_dict(self) -> None:
        uid = 1004
        with self.assertRaises(ValueError) as cm:
            self.usm_mod.user_session_manager.set_session(uid, {"chat": "x"})  # type: ignore[arg-type]
        self.assertIn("chat must be a dict", str(cm.exception))

    # [COMMON-SESSION:T01-01-07] 空白のみは ValueError
    def test_07_requires_non_blank_provider_model(self) -> None:
        uid = 1005
        with self.assertRaises(ValueError):
            self.usm_mod.user_session_manager.set_session(uid, {"chat": {"provider": "   ", "model": "gpt"}})
        with self.assertRaises(ValueError):
            self.usm_mod.user_session_manager.set_session(uid, {"chat": {"provider": "openai", "model": "   "}})

    # [COMMON-SESSION:T01-01-08] 起動時ロード例外復旧（sessions={} & "{}" 書き戻し）
    def test_08_init_load_exception_recovers_empty(self) -> None:
        usm_mod = self.usm_mod
        with patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.read_text", side_effect=Exception("boom")), \
             patch("pathlib.Path.write_text") as mock_write:
            reloaded = importlib.reload(usm_mod)
            mgr = reloaded.UserSessionManager()
            self.assertEqual(mgr.sessions, {})
            mock_write.assert_called()  # "{}" で復旧

    # [COMMON-SESSION:T01-01-09] 起動時ロード（exists False）| 空の sessions で起動
    def test_09_init_path_not_exists_keeps_empty(self) -> None:
        usm_mod = self.usm_mod
        with patch("pathlib.Path.exists", return_value=False):
            reloaded = importlib.reload(usm_mod)
            mgr = reloaded.UserSessionManager()
            self.assertEqual(mgr.sessions, {})


# test_xxx -> (番号, 説明)
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

if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(UserSessionManagerSpecTest)
    run_unittest_suite("COMMON-SESSION:T01-01 common/session/user_session_manager", suite, mapping)
