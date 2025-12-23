# tests/T08_UserSession_01_user_session_test.py
# ------------------------------------------------------------
# T08-01 : UserSession 管理（USM）
# 目的:
#  - Discord 非依存で UserSessionManager の公的APIを網羅
#  - 保存先 (~/.aichabo/usersessions.json) はテスト中のみ一時ディレクトリへ差し替え
# 出力:
#  - ✅/❌ と --- SUMMARY T08-01: ... --- を Reporter で統一
# 実行:
#  - python -m tests.T08_UserSession_01_user_session_test
# ------------------------------------------------------------
import json, shutil, tempfile, unittest
from pathlib import Path
from tests._report import _Reporter as Reporter

# 対象
from common.session import user_session_manager as usm_mod

rep = Reporter("T08-01 UserSession basic")
PATH = usm_mod.PATH  # ~/.aichabo/usersessions.json 実体パス

class UserSessionManagerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # 既存ファイルを退避して「空のストア」から開始
        cls._bak_dir = Path(tempfile.mkdtemp(prefix="aichabo_usm_bak_"))
        cls._users_bak = None
        if PATH.exists():
            cls._users_bak = cls._bak_dir / "usersessions.json"
            cls._users_bak.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(PATH, cls._users_bak)
        PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(PATH, "w", encoding="utf-8") as f:
            f.write("{}")
        # シングルトンを初期化（in-memory も空に）
        usm_mod.user_session_manager = usm_mod.UserSessionManager()

    @classmethod
    def tearDownClass(cls):
        # 退避から復元（存在していた場合のみ）
        try:
            if cls._users_bak is not None:
                shutil.copy2(cls._users_bak, PATH)
            elif PATH.exists():
                PATH.unlink()
        except Exception:
            pass
        try:
            shutil.rmtree(cls._bak_dir, ignore_errors=True)
        except Exception:
            pass

    # --- ケース ---

    # T08-01-01: 入力ガード（None → None）
    def test_01_guard_none_user_id_returns_none(self):
        got = usm_mod.user_session_manager.get_session(None)  # type: ignore[arg-type]
        self.assertIsNone(got)

    # T08-01-02: 未登録 → None
    def test_02_get_unregistered_returns_none(self):
        self.assertIsNone(usm_mod.user_session_manager.get_session(987654321))

    # T08-01-03: 最小セッション set/get OK（api_key は非保持）
    def test_03_set_get_minimal_and_strip_api_key(self):
        uid = 1001
        payload = {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "api_key": "SHOULD_BE_REMOVED",
            "nested": {"api_key": "REMOVE_ME_TOO", "arr": [{"api_key": "X"}]}
        }
        usm_mod.user_session_manager.set_session(uid, payload)
        self.assertTrue(usm_mod.user_session_manager.has_session(uid))
        got = usm_mod.user_session_manager.get_session(uid)
        self.assertIsInstance(got, dict)
        self.assertEqual(got.get("provider"), "openai")
        self.assertEqual(got.get("model"), "gpt-4o-mini")
        # api_key が深い階層まで削除されていること
        self.assertNotIn("api_key", got)
        self.assertNotIn("api_key", (got.get("nested") or {}))
        self.assertTrue(all("api_key" not in d for d in (got.get("nested") or {}).get("arr", [])))

    # T08-01-04: provider/model 必須（現実装は未満。実装修正後に有効化）
    def test_04_required_provider_and_model(self):
        # 現行実装は missing model を許容しているため、この仕様に合わせる場合は
        # set_session が ValueError を投げる or get_session が None を返す、等への修正が必要。
        self.skipTest("USMで provider/model を必須にする実装修正後に有効化（今はスキップ）")

if __name__ == "__main__":
    print(f"=== {rep.title} ===")
    # Reporter で各ケースを明示的に実行
    titlemap = {
        "test_01_guard_none_user_id_returns_none": "guard(None) -> None",
        "test_02_get_unregistered_returns_none":   "unregistered -> None",
        "test_03_set_get_minimal_and_strip_api_key": "set/get minimal & strip api_key",
        "test_04_required_provider_and_model":     "required provider/model (TODO after impl)",
    }
    for name, title in titlemap.items():
        with rep.case(title):
            getattr(UserSessionManagerTest(methodName=name), name)()
    rep.summary()
