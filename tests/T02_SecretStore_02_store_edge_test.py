# tests/T02_SecretStore_02_store_edge_test.py
# ------------------------------------------------------------
# T02-02 : SecretStore edges & recovery
# 目的:
#  - 例外・境界・復旧系の網羅で coverage を底上げ
# スコープ:
#  - common/secret/store.py の分岐・例外・復旧
# 依存:
#  - 既存の SecretStore シングルトン (store) とモジュール定数
# 注意:
#  - 実ストア (~/.aichabo/secretstore) を汚さないように
#    USERS_JSON / SERVERS_JSON をバックアップ → 復元する

import os
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tests._report import _Reporter as Reporter

# テスト対象
from common.secret.store import store, USERS_JSON, SERVERS_JSON, MASTER_KEY_PATH

rep = Reporter("T02-02 SecretStore edges & recovery")
PROV = "openai"  # 正規化済み名称（小文字）
UID_BASE = 990000
GID_BASE = 880000


def _fresh_ids():
    # 連続実行でも衝突しないように一意な ID を生成
    # （1テスト毎に増分）
    _fresh_ids.counter += 1
    return UID_BASE + _fresh_ids.counter, GID_BASE + _fresh_ids.counter
_fresh_ids.counter = 0


class SecretStoreEdgeTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # 既存ファイルを退避
        cls._backup_dir = Path(tempfile.mkdtemp(prefix="aichabo_ss_backup_"))
        cls._users_bak = None
        cls._servers_bak = None
        for src, name in ((USERS_JSON, "users.json"), (SERVERS_JSON, "servers.json")):
            if Path(src).exists():
                dst = cls._backup_dir / name
                shutil.copy2(src, dst)
                if "users" in name:
                    cls._users_bak = dst
                else:
                    cls._servers_bak = dst
        # テストを常に「空のストア」から開始（バックアップは tearDownClass で復元）
        Path(USERS_JSON).parent.mkdir(parents=True, exist_ok=True)
        with open(USERS_JSON, "w", encoding="utf-8") as f:
            f.write("{}")
        with open(SERVERS_JSON, "w", encoding="utf-8") as f:
            f.write("{}")

    @classmethod
    def tearDownClass(cls):
        # 退避から復元（存在していたものだけ）
        try:
            if cls._users_bak is not None:
                shutil.copy2(cls._users_bak, USERS_JSON)
            elif Path(USERS_JSON).exists():
                # 元が無かったなら消す
                Path(USERS_JSON).unlink()
        except Exception:
            pass
        try:
            if cls._servers_bak is not None:
                shutil.copy2(cls._servers_bak, SERVERS_JSON)
            elif Path(SERVERS_JSON).exists():
                Path(SERVERS_JSON).unlink()
        except Exception:
            pass
        try:
            shutil.rmtree(cls._backup_dir, ignore_errors=True)
        except Exception:
            pass

    # T02-02-01: put_user_key 空 provider → ValueError
    def test_01_put_user_empty_provider_raises(self):
        uid, _ = _fresh_ids()
        with self.assertRaises(ValueError):
            store.put_user_key(uid, "", b"xyz")
        with self.assertRaises(ValueError):
            store.put_user_key(uid, None, b"xyz")  # type: ignore[arg-type]

    # T02-02-02: put_server_key 空 provider → ValueError
    def test_02_put_server_empty_provider_raises(self):
        _, gid = _fresh_ids()
        with self.assertRaises(ValueError):
            store.put_server_key(gid, "", b"xyz")
        with self.assertRaises(ValueError):
            store.put_server_key(gid, None, b"xyz")  # type: ignore[arg-type]

    # T02-02-03: get_user_key 空 provider → None
    def test_03_get_user_empty_provider_returns_none(self):
        uid, _ = _fresh_ids()
        self.assertIsNone(store.get_user_key(uid, ""))   # 空
        self.assertIsNone(store.get_user_key(uid, None)) # type: ignore[arg-type]

    # T02-02-04: get_server_key 空 provider → None
    def test_04_get_server_empty_provider_returns_none(self):
        _, gid = _fresh_ids()
        self.assertIsNone(store.get_server_key(gid, ""))   # 空
        self.assertIsNone(store.get_server_key(gid, None)) # type: ignore[arg-type]

    # T02-02-05: has_server_any_key False → True
    def test_05_has_server_any_key_false_true(self):
        _, gid = _fresh_ids()
        # 念のため事前掃除（存在しても例外にならない仕様）
        store.delete_server_keys(gid)
        self.assertFalse(store.has_server_any_key(gid))  # ここは常に False で安定
        store.put_server_key(gid, PROV, b"tok")
        self.assertTrue(store.has_server_any_key(gid))

    # T02-02-06: delete_server_keys 安全（存在しなくても例外なし）
    def test_06_delete_server_keys_is_safe(self):
        _, gid = _fresh_ids()
        # 無い gid でも例外にならない
        store.delete_server_keys(gid)
        # 事後も当然 False
        self.assertFalse(store.has_server_any_key(gid))

    # T02-02-07: 後方互換 - 'fernet:' なしでも復号できる
    def test_07_backward_compat_no_prefix(self):
        uid, _ = _fresh_ids()
        # 正規の保存で暗号文を作る
        store.put_user_key(uid, PROV, b"SAMPLE")
        # users.json を直接開いて、'fernet:' を剥がしたトークンを埋める
        with open(USERS_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
        enc = data[str(uid)]["providers"][PROV]
        assert enc.startswith("fernet:")
        raw = enc[len("fernet:"):]
        data[str(uid)]["providers"][PROV] = raw
        with open(USERS_JSON, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        # 取り出しで bytes が得られる（_dec 内で接頭辞無しを許容）
        got = store.get_user_key(uid, PROV)
        self.assertEqual(got, b"SAMPLE")

    # T02-02-08: 壊れた JSON を自動復旧（_load_json の復旧経路）
    def test_08_load_json_recovery(self):
        # users.json をわざと壊す
        Path(USERS_JSON).parent.mkdir(parents=True, exist_ok=True)
        with open(USERS_JSON, "w", encoding="utf-8") as f:
            f.write("{ this_is: not json")
        # API 経由の読みで復旧（空辞書に置き換え）→ get_user_keys は {} を返す
        uid, _ = _fresh_ids()
        keys = store.get_user_keys(uid)
        self.assertEqual(keys, {})
        # 復旧後は正しい JSON になっていること
        with open(USERS_JSON, "r", encoding="utf-8") as f:
            json.load(f)  # パースできればOK

    # T02-02-09: delete_user_keys の安全性（存在していても「空化」で終わる）
    def test_09_delete_user_keys_clears_providers(self):
        uid, _ = _fresh_ids()
        store.put_user_key(uid, PROV, b"abc")
        self.assertIsNotNone(store.get_user_key(uid, PROV))
        store.delete_user_keys(uid)
        self.assertEqual(store.get_user_keys(uid), {})


if __name__ == "__main__":
    SUITE_TITLE = "T02-02 SecretStore edges & recovery"
    print(f"=== {SUITE_TITLE} ===")
    print(f"Secret backend: {store.backend_name()}")
    # 共通レポータの体裁で出す（❌/✅ + CASE 番号）
    titlemap = {
        "test_01_put_user_empty_provider_raises":   "put_user empty provider -> ValueError",
        "test_02_put_server_empty_provider_raises": "put_server empty provider -> ValueError",
        "test_03_get_user_empty_provider_returns_none": "get_user empty provider -> None",
        "test_04_get_server_empty_provider_returns_none": "get_server empty provider -> None",
        "test_05_has_server_any_key_false_true": "has_server_any_key False/True",
        "test_06_delete_server_keys_is_safe":    "delete_server_keys safe",
        "test_07_backward_compat_no_prefix":     "backward compat w/o prefix",
        "test_08_load_json_recovery":            "broken JSON -> recovery",
        "test_09_delete_user_keys_clears_providers": "delete_user_keys clears providers",
    }
    for name, title in titlemap.items():
        with rep.case(title):
            getattr(SecretStoreEdgeTest(methodName=name), name)()
    rep.summary()
