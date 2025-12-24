# -*- coding: utf-8 -*-
"""
COMMON-SESSION:T02 : server_session_manager

対象: common.session.server_session_manager

目的:
- ServerSessionManager の公的APIを Discord 非依存で検証する
  - 共有認証設定（get/set/clear）の実装準拠
  - システムオプション（set/get/clear/all）
- 保存先（PATH_SHARED / PATH_OPTS）をテスト中のみ一時パスへ差し替え、安全に実行する

実装準拠メモ:
- get_shared_auth_config(None) / 未登録 は None ではなく {} を返す
- set_shared_auth_config は provider/model ではなく chat.provider / chat.model を必須とする
  （不足時 ValueError: "chat.provider and chat.model are required"）

テスト番号:
- COMMON-SESSION:T02-01-01 ... （T02=SSM, 01=テストコード, 01..=ケース）

実行:
- python -m tests.common.session.T02_ServerSession_01_server_session_test
"""

import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, Tuple

from tests._report import run_unittest_suite


class ServerSessionManagerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from common.session import server_session_manager as ssm_mod  # type: ignore
        cls.ssm_mod = ssm_mod

        # 退避
        cls._orig_shared = getattr(ssm_mod, "PATH_SHARED", None)
        cls._orig_opts = getattr(ssm_mod, "PATH_OPTS", None)
        cls._orig_singleton = getattr(ssm_mod, "server_session_manager", None)

        # テスト用パス作成
        cls._tmpdir = Path(tempfile.mkdtemp(prefix="aichabo_ssm_"))
        cls._test_shared = cls._tmpdir / "servershared.json"
        cls._test_opts = cls._tmpdir / "serveropts.json"
        cls._test_shared.write_text("{}", encoding="utf-8")
        cls._test_opts.write_text("{}", encoding="utf-8")

        # モジュール定数を差し替え
        ssm_mod.PATH_SHARED = cls._test_shared
        ssm_mod.PATH_OPTS = cls._test_opts

        # シングルトンを作り直す
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

    # [COMMON-SESSION:T02-01-01] guard(None) -> {}
    def test_01_get_shared_auth_config_guard(self):
        out = self.ssm_mod.server_session_manager.get_shared_auth_config(None)  # type: ignore[arg-type]
        self.assertEqual(out, {})

    # [COMMON-SESSION:T02-01-02] 未登録 -> {}
    def test_02_get_shared_auth_config_unregistered(self):
        out = self.ssm_mod.server_session_manager.get_shared_auth_config(555)
        self.assertEqual(out, {})

    # [COMMON-SESSION:T02-01-03] set/get shared auth（chat.provider/chat.model 必須・api_key は非保持）
    def test_03_set_get_shared_auth_config_and_strip_api_key(self):
        gid = 777
        payload: Dict[str, Any] = {
            "chat": {"provider": "openai", "model": "gpt-4o-mini"},
            "api_key": "REMOVE",
        }
        self.ssm_mod.server_session_manager.set_shared_auth_config(gid, payload)

        got = self.ssm_mod.server_session_manager.get_shared_auth_config(gid)
        self.assertIsInstance(got, dict)
        # 実装は chat をネスト保持する想定
        self.assertEqual((got.get("chat") or {}).get("provider"), "openai")
        self.assertEqual((got.get("chat") or {}).get("model"), "gpt-4o-mini")
        self.assertNotIn("api_key", got)

    # [COMMON-SESSION:T02-01-04] clear_shared_auth_config で {} に戻る
    def test_04_clear_shared_auth_config(self):
        gid = 778
        self.ssm_mod.server_session_manager.set_shared_auth_config(
            gid, {"chat": {"provider": "openai", "model": "gpt"}}
        )
        self.ssm_mod.server_session_manager.clear_shared_auth_config(gid)
        self.assertEqual(self.ssm_mod.server_session_manager.get_shared_auth_config(gid), {})

    # [COMMON-SESSION:T02-01-05] set_shared_auth_config: 必須不足なら ValueError
    def test_05_set_shared_auth_config_requires_chat_provider_model(self):
        gid = 779
        with self.assertRaises(ValueError) as cm:
            self.ssm_mod.server_session_manager.set_shared_auth_config(gid, {"provider": "openai", "model": "gpt"})
        self.assertIn("chat.provider and chat.model are required", str(cm.exception))

    # [COMMON-SESSION:T02-01-06] option: set/get/clear/all
    def test_06_set_get_clear_option(self):
        gid = 999
        self.assertIsNone(self.ssm_mod.server_session_manager.get_option(gid, "printmsg"))
        self.ssm_mod.server_session_manager.set_option(gid, "printmsg", True)
        self.assertTrue(self.ssm_mod.server_session_manager.get_option(gid, "printmsg"))
        self.assertEqual(self.ssm_mod.server_session_manager.all_options(gid), {"printmsg": True})
        self.ssm_mod.server_session_manager.clear_option(gid, "printmsg")
        self.assertIsNone(self.ssm_mod.server_session_manager.get_option(gid, "printmsg"))
        self.assertEqual(self.ssm_mod.server_session_manager.all_options(gid), {})


if __name__ == "__main__":
    mapping: Dict[str, Tuple[str, str]] = {
        "test_01_get_shared_auth_config_guard": ("COMMON-SESSION:T02-01-01", "guard(None) -> {}"),
        "test_02_get_shared_auth_config_unregistered": ("COMMON-SESSION:T02-01-02", "unregistered -> {}"),
        "test_03_set_get_shared_auth_config_and_strip_api_key": ("COMMON-SESSION:T02-01-03", "set/get shared auth & strip api_key"),
        "test_04_clear_shared_auth_config": ("COMMON-SESSION:T02-01-04", "clear_shared_auth_config -> {}"),
        "test_05_set_shared_auth_config_requires_chat_provider_model": ("COMMON-SESSION:T02-01-05", "requires chat.provider/chat.model -> ValueError"),
        "test_06_set_get_clear_option": ("COMMON-SESSION:T02-01-06", "option set/get/clear/all"),
    }
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ServerSessionManagerTest)
    run_unittest_suite("COMMON-SESSION:T02 common/session/server_session_manager", suite, mapping)
