# utiltests/T09_ServerSession_01_server_session_test.py
# ------------------------------------------------------------
# T09-01 : ServerSession 管理（SSM）
# 目的:
#  - 共有認証設定(set/get/clear) と システムオプション(set/get/clear) の基本動作
#  - 保存先 (~/.aichabo/server*.json) はテスト中のみ空から開始
# 出力:
#  - ✅/❌ と --- SUMMARY T09-01: ... --- を Reporter で統一
# 実行:
#  - python -m utiltests.T09_ServerSession_01_server_session_test
# ------------------------------------------------------------
import json, shutil, tempfile, unittest
from pathlib import Path
from utiltests._report import _Reporter as Reporter

# 対象
from common.session import server_session_manager as ssm_mod

rep = Reporter("T09-01 ServerSession basic")
PATH_SHARED = ssm_mod.PATH_SHARED
PATH_OPTS   = ssm_mod.PATH_OPTS

class ServerSessionManagerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # 既存ファイル退避 → 空ストア
        cls._bak_dir = Path(tempfile.mkdtemp(prefix="aichabo_ssm_bak_"))
        cls._shared_bak = None
        cls._opts_bak = None
        if PATH_SHARED.exists():
            cls._shared_bak = cls._bak_dir / "servershared.json"
            shutil.copy2(PATH_SHARED, cls._shared_bak)
        if PATH_OPTS.exists():
            cls._opts_bak = cls._bak_dir / "serveropts.json"
            shutil.copy2(PATH_OPTS, cls._opts_bak)
        PATH_SHARED.parent.mkdir(parents=True, exist_ok=True)
        with open(PATH_SHARED, "w", encoding="utf-8") as f:
            f.write("{}")
        with open(PATH_OPTS, "w", encoding="utf-8") as f:
            f.write("{}")
        # シングルトン初期化
        ssm_mod.server_session_manager = ssm_mod.ServerSessionManager()

    @classmethod
    def tearDownClass(cls):
        try:
            if cls._shared_bak is not None:
                shutil.copy2(cls._shared_bak, PATH_SHARED)
            elif PATH_SHARED.exists():
                PATH_SHARED.unlink()
        except Exception:
            pass
        try:
            if cls._opts_bak is not None:
                shutil.copy2(cls._opts_bak, PATH_OPTS)
            elif PATH_OPTS.exists():
                PATH_OPTS.unlink()
        except Exception:
            pass
        try:
            shutil.rmtree(cls._bak_dir, ignore_errors=True)
        except Exception:
            pass

    # --- 共有認証 ---

    # T09-01-01: None guard -> None
    def test_01_get_shared_auth_config_guard(self):
        self.assertIsNone(ssm_mod.server_session_manager.get_shared_auth_config(None))  # type: ignore[arg-type]

    # T09-01-02: 未登録 -> None
    def test_02_get_shared_auth_config_unregistered(self):
        self.assertIsNone(ssm_mod.server_session_manager.get_shared_auth_config(555))

    # T09-01-03: 正常 set/get（api_key は非保持）
    def test_03_set_get_shared_auth_config_and_strip_api_key(self):
        gid = 777
        payload = {"provider":"openai","model":"gpt-4o-mini","api_key":"REMOVE"}
        ssm_mod.server_session_manager.set_shared_auth_config(gid, payload)
        got = ssm_mod.server_session_manager.get_shared_auth_config(gid)
        self.assertEqual(got, {"provider":"openai","model":"gpt-4o-mini"})

    # T09-01-04: clear_shared_auth_config で削除
    def test_04_clear_shared_auth_config(self):
        gid = 778
        ssm_mod.server_session_manager.set_shared_auth_config(gid, {"provider":"openai","model":"gpt"})
        ssm_mod.server_session_manager.clear_shared_auth_config(gid)
        self.assertIsNone(ssm_mod.server_session_manager.get_shared_auth_config(gid))

    # T09-01-05: provider/model 必須（現実装は未満。実装修正後に有効化）
    def test_05_required_provider_and_model(self):
        self.skipTest("SSMで provider/model を必須にする実装修正後に有効化（今はスキップ）")

    # --- システムオプション ---

    # T09-01-06: set/get/clear option
    def test_06_set_get_clear_option(self):
        gid = 999
        self.assertIsNone(ssm_mod.server_session_manager.get_option(gid, "printmsg"))
        ssm_mod.server_session_manager.set_option(gid, "printmsg", True)
        self.assertTrue(ssm_mod.server_session_manager.get_option(gid, "printmsg"))
        self.assertEqual(ssm_mod.server_session_manager.all_options(gid), {"printmsg": True})
        ssm_mod.server_session_manager.clear_option(gid, "printmsg")
        self.assertIsNone(ssm_mod.server_session_manager.get_option(gid, "printmsg"))
        self.assertEqual(ssm_mod.server_session_manager.all_options(gid), {})

if __name__ == "__main__":
    print(f"=== {rep.title} ===")
    titlemap = {
        "test_01_get_shared_auth_config_guard": "get_shared_auth_config(None) -> None",
        "test_02_get_shared_auth_config_unregistered": "unregistered -> None",
        "test_03_set_get_shared_auth_config_and_strip_api_key": "set/get shared & strip api_key",
        "test_04_clear_shared_auth_config": "clear_shared_auth_config",
        "test_05_required_provider_and_model": "required provider/model (TODO after impl)",
        "test_06_set_get_clear_option": "set/get/clear option",
    }
    for name, title in titlemap.items():
        with rep.case(title):
            getattr(ServerSessionManagerTest(methodName=name), name)()
    rep.summary()
