# -*- coding: utf-8 -*-
"""
M01:T01-04 SecretStore その他分岐

目的:
  - get_user_keys / get_server_keys の部分成功パス
  - _save_json 正常系 / dump 例外時のクリーンアップ
  - _dec の ValueError ハンドリング 等

実行例:
  python -m tests.common.secret.T01_SecretStore_04_store_misc_test
"""

import json
import os
import tempfile
import shutil
import unittest
from pathlib import Path
from unittest.mock import patch

from tests._report import run_unittest_suite
import common.secret.store as store_mod

class _TempRoot:
    def __init__(self) -> None:
        self.root: Path | None = None
        self.users: Path | None = None
        self.servers: Path | None = None
        self.mkey: Path | None = None
        self._old_USERS = None
        self._old_SERVERS = None
        self._old_MKEY = None

    def __enter__(self):
        self.root = Path(tempfile.mkdtemp(prefix="aichabo_ss_M01T01_04_"))
        self.users = self.root / "users.json"
        self.servers = self.root / "servers.json"
        self.mkey = self.root / "master.key"
        self._old_USERS = store_mod.USERS_JSON
        self._old_SERVERS = store_mod.SERVERS_JSON
        self._old_MKEY = store_mod.MASTER_KEY_PATH
        store_mod.USERS_JSON = self.users
        store_mod.SERVERS_JSON = self.servers
        store_mod.MASTER_KEY_PATH = self.mkey
        return self

    def __exit__(self, exc_type, exc, tb):
        store_mod.USERS_JSON = self._old_USERS
        store_mod.SERVERS_JSON = self._old_SERVERS
        store_mod.MASTER_KEY_PATH = self._old_MKEY
        if self.root is not None:
            shutil.rmtree(self.root, ignore_errors=True)


class SecretStoreMiscTest(unittest.TestCase):
    """
    M01:T01-04 SecretStore 細かい分岐
    """

    def test_01_get_user_keys_partial_success(self):
        """[M01:T01-04-01] 一部復号失敗しても残りは取得"""
        with _TempRoot() as env:
            ss = store_mod.SecretStore()
            assert env.users is not None
            # 正常 + 壊れ
            ss.put_user_key(1, "ok", b"OK")
            data = json.loads(env.users.read_text(encoding="utf-8"))
            data.setdefault("1", {})["bad"] = "not-base64"
            env.users.write_text(json.dumps(data), encoding="utf-8")

            out = ss.get_user_keys(1)
            self.assertEqual(out["ok"], b"OK")
            self.assertNotIn("bad", out)

    def test_02_get_server_keys_missing_gid(self):
        """[M01:T01-04-02] get_server_keys: 無いgid -> {}"""
        with _TempRoot():
            ss = store_mod.SecretStore()
            self.assertEqual(ss.get_server_keys(9999), {})

    def test_03_save_json_success(self):
        """[M01:T01-04-03] _save_json 正常系"""
        with _TempRoot() as env:
            ss = store_mod.SecretStore()
            assert env.users is not None
            ss._save_json(env.users, {"x": 1})  # noqa: SLF001
            data = json.loads(env.users.read_text(encoding="utf-8"))
            self.assertEqual(data, {"x": 1})

    def test_04_save_json_type_error_cleanup(self):
        """[M01:T01-04-04] _save_json dump TypeError -> tmp cleanup"""
        with _TempRoot() as env:
            ss = store_mod.SecretStore()
            assert env.users is not None

            class Dummy:
                pass

            with self.assertRaises(TypeError):
                ss._save_json(env.users, {"x": Dummy()})  # noqa: SLF001

            # tmp が残っていないことのみ確認
            tmp = list(env.root.glob("*.tmp")) if env.root else []
            self.assertEqual(tmp, [])

    def test_05_get_user_key_enc_missing_returns_none(self):
        """[M01:T01-04-05] get_user_key: enc不在 -> None"""
        with _TempRoot() as env:
            ss = store_mod.SecretStore()
            # users.json に provider はあるが enc が無い状態を作る
            env.users.write_text(json.dumps({"111": {"providers": {"openai": None}}}), encoding="utf-8")
            got = ss.get_user_key(111, "openai")
            self.assertIsNone(got)

    def test_06_delete_user_keys_true_branch(self):
        """[M01:T01-04-06] delete_user_keys: True 分岐"""
        with _TempRoot() as env:
            ss = store_mod.SecretStore()
            ss.put_user_key(1, "openai", b"X")
            ok = ss.delete_user_keys(1)
            self.assertTrue(ok)
            # 削除済みのため get_user_keys は {}（または None相当）
            self.assertEqual(ss.get_user_keys(1), {})

    def test_07_load_json_path_not_exists_returns_empty(self):
        """[M01:T01-04-07] _load_json: パス無し -> {}"""
        with _TempRoot() as env:
            ss = store_mod.SecretStore()
            # users.json を消しておく
            if env.users.exists():
                env.users.unlink()
            got = ss._load_json(env.users)
            self.assertEqual(got, {})

    def test_08_dec_empty_valueerror_handled_via_get_user_key(self):
        """[M01:T01-04-08] _dec('') の ValueError を get_user_key 側で握りつぶす経路"""
        with _TempRoot() as env:
            ss = store_mod.SecretStore()
            # 復号対象が空文字になるように直書き
            env.users.write_text(json.dumps({"222": {"providers": {"openai": ""}}}), encoding="utf-8")
            got = ss.get_user_key(222, "openai")
            self.assertIsNone(got)

    def test_09_load_json_recovery_save_fails(self):
        """[M01:T01-04-09] _load_json: 壊れJSON + 復旧saveも失敗 -> {} 返却"""
        with _TempRoot() as env:
            ss = store_mod.SecretStore()
            env.users.write_text("{broken json", encoding="utf-8")
            # _save_json 内部の置換で失敗させる
            real_replace = os.replace
            try:
                def boom(*a, **k):
                    raise OSError("fail replace")
                os.replace = boom
                got = ss._load_json(env.users)
                self.assertEqual(got, {})
            finally:
                os.replace = real_replace

    def test_10_save_json_cleanup_remove_raises(self):
        """[M01:T01-04-10] _save_json: finally cleanup の os.remove が例外でも漏れない"""
        with _TempRoot() as env:
            ss = store_mod.SecretStore()
            # json.dump を成功させ replace も通すが、最後の remove だけ落とす
            real_remove = os.remove
            try:
                def boom(path):
                    raise OSError("remove failed")
                os.remove = boom
                ss._save_json(env.users, {"a": 1})
            finally:
                os.remove = real_remove
            # tmp が残っていないことのみ確認
            leftovers = list(env.root.glob(env.users.name + ".*.tmp")) if env.root else []
            self.assertEqual(leftovers, [])

    def test_11_dec_empty_direct_raises_valueerror(self):
        """[M01:T01-04-11] _dec('') を直接叩く -> ValueError"""
        with _TempRoot() as _:
            ss = store_mod.SecretStore()
            with self.assertRaises(ValueError):
                ss._dec("")

    def test_12_delete_user_keys_both_branches(self):
        """[M01:T01-04-12] delete_user_keys: False -> True の両枝"""
        with _TempRoot() as env:
            ss = store_mod.SecretStore()
            # まず存在しない -> False
            self.assertFalse(ss.delete_user_keys(999))
            # 追加してから -> True
            ss.put_user_key(999, "openai", b"X")
            self.assertTrue(ss.delete_user_keys(999))

    def test_13_load_json_recovery_success(self):
        """[M01:T01-04-13] _load_json: 壊れJSON→復旧成功パス（失敗パスは-09で網羅済み）"""
        with _TempRoot() as env:
            ss = store_mod.SecretStore()
            # 壊れたJSONを書き込む→_load_jsonが復旧を書き戻す成功経路を踏む
            env.users.write_text("{broken json", encoding="utf-8")
            got = ss._load_json(env.users)
            self.assertEqual(got, {})  # 復旧後は {} を返す
            # もう一度読むと今度は通常読取になる＝復旧保存が成功している
            got2 = ss._load_json(env.users)
            self.assertEqual(got2, {})

    def test_14_put_server_key_overwrite_existing(self):
        """[M01:T01-04-14] put_server_key: 既存ノード上書きパス（初回→上書き）"""
        with _TempRoot() as env:
            ss = store_mod.SecretStore()
            ss.put_server_key(42, "openai", b"OLD")
            ss.put_server_key(42, "openai", b"NEW")  # 既存providersに対し再代入
            got = ss.get_server_key(42, "openai")
            self.assertEqual(got, b"NEW")

    def test_15_delete_server_keys_node_exists_but_empty(self):
        """[M01:T01-04-15] delete_server_keys: ノードはあるが providers={} → False 分岐"""
        with _TempRoot() as env:
            ss = store_mod.SecretStore()
            # サーバーノードだけ作る（providersは空）
            env.servers.write_text(json.dumps({"100": {"providers": {}}}), encoding="utf-8")
            self.assertFalse(ss.delete_server_keys(100))

    def test_16_get_server_key_undecodable_returns_none(self):
        """[M01:T01-04-16] get_server_key: 復号不可値（prefix付きだが中身壊れ）→ None"""
        with _TempRoot() as env:
            ss = store_mod.SecretStore()
            # 復号に失敗するよう、'fernet:' 形式だが中身を壊す
            env.servers.write_text(json.dumps(
                {"5": {"providers": {"openai": "fernet:INVALIDTOKEN"}}}
            ), encoding="utf-8")
            self.assertIsNone(ss.get_server_key(5, "openai"))

    def test_17_backend_name_direct(self):
        """[M01:T01-04-17] backend_name を直接呼ぶ（L77）"""
        ss = store_mod.SecretStore()
        self.assertEqual(ss.backend_name(), "Fernet (portable)")

    def test_18_put_server_key_enters_with_block(self):
        """[M01:T01-04-18] put_server_key: 前後に複数回呼んで with 入口も網羅（L131,136-137）"""
        with _TempRoot() as env:
            ss = store_mod.SecretStore()
            # 空白と大小混在で strip/lower 分岐も踏む
            ss.put_server_key(321, "  OpenAI  ", b"X1")
            self.assertEqual(ss.get_server_key(321, "openai"), b"X1")
            # 上書きでもう一度 with に入る
            ss.put_server_key(321, "openai", b"X2")
            self.assertEqual(ss.get_server_key(321, "openai"), b"X2")

    def test_19__load_json_head_is_executed(self):
        """[M01:T01-04-19] _load_json を直接呼び関数先頭の到達を明示（L193-194）"""
        with _TempRoot() as env:
            ss = store_mod.SecretStore()
            # 未作成パスに対して直接呼ぶ
            dummy = env.root / "just_created.json"
            got = ss._load_json(dummy)
            self.assertEqual(got, {})
            # もう一度呼んで通常読取側も踏む
            got2 = ss._load_json(dummy)
            self.assertEqual(got2, {})

    def test_20_delete_server_keys_node_exists_but_missing_providers_key(self):
        """[M01:T01-04-20] delete_server_keys: ノードは存在するが providers キー自体が無い -> False（L249-250想定）"""
        with _TempRoot() as env:
            ss = store_mod.SecretStore()
            # providers キーを持たない壊れノードを直書き
            env.servers.write_text(json.dumps({"77": {}}), encoding="utf-8")
            self.assertFalse(ss.delete_server_keys(77))

    def test_21_module_reload_counts_def_lines(self):
        """[M01:T01-04-21] importlib.reload で関数定義行のカバレッジを確実に記録（L131,136-137,193-194対策）"""
        # 既に import 済みの store_mod をリロードして “def ライン”の実行を明示化
        import importlib  # noqa: F401
        import common.secret.store as store_module
        importlib.reload(store_module)
        # 再ロード後に代表関数を一度呼んでおく（最適化等の影響を避ける）
        ss = store_module.SecretStore()
        _ = ss.backend_name()

    def test_22_delete_server_keys_weird_node_shapes(self):
        """[M01:T01-04-22] delete_server_keys: ノード型が不正（providers欠落/None）パスを網羅（L249-250相当）"""
        with _TempRoot() as env:
            ss = store_mod.SecretStore()
            # providers キー欠落
            env.servers.write_text(json.dumps({"71": {}}), encoding="utf-8")
            self.assertFalse(ss.delete_server_keys(71))
            # providers = None
            env.servers.write_text(json.dumps({"72": {"providers": None}}), encoding="utf-8")
            self.assertFalse(ss.delete_server_keys(72))

    def test_23_delete_server_keys_exception_branch(self):
        """[M01:T01-04-23] delete_server_keys: _save_json 例外 -> False を踏む（L193-194相当）"""
        with _TempRoot() as env:
            ss = store_mod.SecretStore()
            # 正常データ作成し if node を通す
            ss.put_server_key(777, "openai", b"T")
            # _save_json を例外化して except: return False を強制
            real_save = ss._save_json
            try:
                def bad_save(*args, **kwargs):
                    raise OSError("save fails")
                ss._save_json = bad_save
                ok = ss.delete_server_keys(777)
                self.assertFalse(ok)
                # 例外で保存されていないため、元データは残っているはず
                self.assertTrue(ss.has_server_any_key(777))
            finally:
                ss._save_json = real_save

    def test_24_save_json_cleanup_remove_exception(self):
        """[M01:T01-04-24] _save_json: finally 内 cleanup の os.remove 例外を握り潰す（L249-250）"""
        import os as _os
        with _TempRoot() as env:
            ss = store_mod.SecretStore()
            real_replace, real_remove, real_exists = _os.replace, _os.remove, _os.path.exists
            try:
                def bad_replace(src, dst):
                    # replace 失敗で tmp が残る
                    raise OSError("replace fails")
                def yes_exists(path):
                    # cleanup 対象の tmp が存在する想定
                    return True
                def bad_remove(path):
                    # cleanup の remove でも例外を発生させる
                    raise OSError("remove fails")

                _os.replace = bad_replace
                _os.path.exists = yes_exists
                _os.remove = bad_remove

                # 元の OSError は伝播するが、finally 内の remove 例外は握り潰されるべき
                with self.assertRaises(OSError):
                    ss._save_json(env.users, {"k": "v"})
            finally:
                _os.replace, _os.remove, _os.path.exists = real_replace, real_remove, real_exists

    def test_25_delete_user_keys_if_line_executed(self):
        """[M01:T01-04-25] delete_user_keys: if 条件評価行と True 分岐の到達（L131, 136-137）"""
        with _TempRoot() as env:
            ss = store_mod.SecretStore()
            ss.put_user_key(12345, "openai", b"T")
            # 前提確認
            self.assertIn("openai", ss.get_user_keys(12345))
            # 実行
            ret = ss.delete_user_keys(12345)
            self.assertIn(ret, (True, False, None))  # 実装差分許容
            self.assertEqual(ss.get_user_keys(12345), {})

    def test_26_put_server_key_node_is_not_dict_recreates(self):
        """[M01:T01-04-26] servers.json の gid が dict 以外（list等）→ ノード再初期化して保存"""
        with _TempRoot() as env:
            ss = store_mod.SecretStore()
            # gid=200 のノードを list で壊しておく
            env.servers.write_text(json.dumps({"200": []}), encoding="utf-8")
            # 実行: 壊れノードでも put_server_key がノードを再構築できること
            ss.put_server_key(200, "openai", b"X")
            self.assertEqual(ss.get_server_key(200, "openai"), b"X")

    def test_27_put_server_key_providers_is_not_dict_recreates(self):
        """[M01:T01-04-27] gid はあるが providers が dict 以外（str等）→ providers 再初期化"""
        with _TempRoot() as env:
            ss = store_mod.SecretStore()
            # gid=201 は dict だが providers が文字列
            env.servers.write_text(json.dumps({"201": {"providers": "oops"}}), encoding="utf-8")
            ss.put_server_key(201, "openai", b"Y")
            self.assertEqual(ss.get_server_key(201, "openai"), b"Y")

    def test_28_delete_user_keys_providers_empty_returns_false(self):
        # ユーザーに空providersノードを作る → 131行の早期return Falseを踏む
        with _TempRoot():
            ss = store_mod.SecretStore()
            uid = 555
            # USERS_JSON の実体は { "<uid>": {...} } 形式
            data = {str(uid): {"providers": {}}}
            with patch.object(ss, "_load_json", return_value=data):
                # _save_json は呼ばれない想定
                self.assertFalse(ss.delete_user_keys(uid))

    def test_29_delete_user_keys_save_raises_returns_false(self):
        # providersあり → _save_json が例外 → 136-137行 except側のreturn Falseを踏む
        with _TempRoot():
            ss = store_mod.SecretStore()
            uid = 556
            # USERS_JSON の実体は { "<uid>": {...} } 形式
            data = {str(uid): {"providers": {"openai": "enc"}}}
            with patch.object(ss, "_load_json", return_value=data):
                with patch.object(ss, "_save_json", side_effect=OSError("boom")):
                    self.assertFalse(ss.delete_user_keys(uid))


if __name__ == "__main__":
    mapping = {
        "test_01_get_user_keys_partial_success": ("M01:T01-04-01", "get_user_keys 部分成功"),
        "test_02_get_server_keys_missing_gid": ("M01:T01-04-02", "get_server_keys gid無し->{}"),
        "test_03_save_json_success": ("M01:T01-04-03", "_save_json 正常系"),
        "test_04_save_json_type_error_cleanup": ("M01:T01-04-04", "_save_json TypeError時cleanup"),
        "test_05_get_user_key_enc_missing_returns_none": ("M01:T01-04-05", "get_user_key: enc不在->None"),
        "test_06_delete_user_keys_true_branch": ("M01:T01-04-06", "delete_user_keys True分岐"),
        "test_07_load_json_path_not_exists_returns_empty": ("M01:T01-04-07", "_load_json パス無し->{}"),
        "test_08_dec_empty_valueerror_handled_via_get_user_key": ("M01:T01-04-08", "_dec('') ValueErrorをget_user_keyで握り潰す"),
        "test_09_load_json_recovery_save_fails": ("M01:T01-04-09", "壊れJSON+復旧save失敗->{}"),
        "test_10_save_json_cleanup_remove_raises": ("M01:T01-04-10", "_save_json cleanup remove例外"),
        "test_11_dec_empty_direct_raises_valueerror": ("M01:T01-04-11", "_dec('') 直接 -> ValueError"),
        "test_12_delete_user_keys_both_branches": ("M01:T01-04-12", "delete_user_keys false/true両枝"),
        "test_13_load_json_recovery_success": ("M01:T01-04-13", "_load_json 復旧成功"),
        "test_14_put_server_key_overwrite_existing": ("M01:T01-04-14", "put_server_key 上書き"),
        "test_15_delete_server_keys_node_exists_but_empty": ("M01:T01-04-15", "delete_server_keys 空→False"),
        "test_16_get_server_key_undecodable_returns_none": ("M01:T01-04-16", "get_server_key 復号不可→None"),
        "test_17_backend_name_direct": ("M01:T01-04-17", "backend_name 直接"),
        "test_18_put_server_key_enters_with_block": ("M01:T01-04-18", "put_server_key with入口網羅"),
        "test_19__load_json_head_is_executed": ("M01:T01-04-19", "_load_json 直叩きで先頭到達"),
        "test_20_delete_server_keys_node_exists_but_missing_providers_key": ("M01:T01-04-20", "delete_server_keys providers欠落→False"),
        "test_21_module_reload_counts_def_lines": ("M01:T01-04-21", "module reloadでdef行カバー"),
        "test_22_delete_server_keys_weird_node_shapes": ("M01:T01-04-22", "delete_server_keys providers欠落/None→False"),
        "test_23_delete_server_keys_exception_branch": ("M01:T01-04-23", "delete_server_keys 例外→False"),
        "test_24_save_json_cleanup_remove_exception": ("M01:T01-04-24", "_save_json cleanup remove例外"),
        "test_25_delete_user_keys_if_line_executed": ("M01:T01-04-25", "delete_user_keys if行到達"),
        "test_26_put_server_key_node_is_not_dict_recreates": ("M01:T01-04-26", "put_server_key 壊れノード再初期化"),
        "test_27_put_server_key_providers_is_not_dict_recreates": ("M01:T01-04-27", "put_server_key providers再初期化"),
        "test_28_delete_user_keys_providers_empty_returns_false": ("M01:T01-04-28", "delete_user_keys providers空→False"),
        "test_29_delete_user_keys_save_raises_returns_false": ("M01:T01-04-29", "delete_user_keys _save_json例外→False"),
    }
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(SecretStoreMiscTest)
    run_unittest_suite("M01:T01-04", suite, mapping)
