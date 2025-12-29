# -*- coding: utf-8 -*-
"""
COMMON-UTILS:T07 : thread_utils

対象: common.utils.thread_utils

目的:
- server_id 単位の threads の read/write/add/remove/is_managed
- filter / delete / clean（threads / servers）

実行:
- python -m tests.common.utils.T07_ThreadUtils_01_thread_utils_test
"""

import json
import tempfile
import unittest
from pathlib import Path
from typing import Dict, Tuple
from unittest.mock import patch

from tests._report import run_unittest_suite


class ThreadUtilsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from common.utils import thread_utils as mod  # type: ignore
        cls.mod = mod

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        base = Path(self.td.name)

        self.service = "discord"
        self.base_dir = base / "ui" / self.service / "data" / "threads"
        self.base_dir.mkdir(parents=True, exist_ok=True)

        # THREADS_DIR を一時ディレクトリ配下へ差し替え
        fake_threads_dir = str(base / "ui" / "{service_name}" / "data" / "threads")
        self.patcher = patch.object(self.mod, "THREADS_DIR", fake_threads_dir)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    # [COMMON-UTILS:T07-01-01] get_server_file_path: service/server でパスが組み立つ
    def test_01_get_server_file_path(self):
        p = self.mod.get_server_file_path(self.service, "S1")
        self.assertTrue(p.endswith(str(Path("threads") / "S1.json")))
        self.assertIn(str(Path("ui") / self.service / "data" / "threads"), p)

    # [COMMON-UTILS:T07-01-02] load_server_threads: 未存在は []
    def test_02_load_missing_returns_empty(self):
        out = self.mod.load_server_threads(self.service, "S1")
        self.assertEqual(out, [])

    # [COMMON-UTILS:T07-01-03] save/load: 正常 roundtrip（strip適用）
    def test_03_save_and_load_roundtrip(self):
        self.mod.save_server_threads(self.service, "S1", ["  t1  ", "t2"])
        out = self.mod.load_server_threads(self.service, "S1")
        self.assertEqual(out, ["t1", "t2"])

    # [COMMON-UTILS:T07-01-04] add_thread_to_server: 重複は追加しない
    def test_04_add_thread_no_duplicates(self):
        self.mod.save_server_threads(self.service, "S1", ["t1"])
        self.mod.add_thread_to_server(self.service, "S1", "t1")
        self.mod.add_thread_to_server(self.service, "S1", "t2")
        out = self.mod.load_server_threads(self.service, "S1")
        self.assertEqual(out, ["t1", "t2"])

    # [COMMON-UTILS:T07-01-05] remove_thread_from_server: 存在する場合のみ削除
    def test_05_remove_thread(self):
        self.mod.save_server_threads(self.service, "S1", ["t1", "t2"])
        self.mod.remove_thread_from_server(self.service, "S1", "t1")
        out = self.mod.load_server_threads(self.service, "S1")
        self.assertEqual(out, ["t2"])

        # ないものは no-op
        self.mod.remove_thread_from_server(self.service, "S1", "tX")
        out2 = self.mod.load_server_threads(self.service, "S1")
        self.assertEqual(out2, ["t2"])

    # [COMMON-UTILS:T07-01-06] is_thread_managed: membership 判定
    def test_06_is_thread_managed(self):
        self.mod.save_server_threads(self.service, "S1", ["t1"])
        self.assertTrue(self.mod.is_thread_managed(self.service, "S1", "t1"))
        self.assertFalse(self.mod.is_thread_managed(self.service, "S1", "t2"))

    # [COMMON-UTILS:T07-01-07] filter_existing_threads: current_ids に存在するものだけ
    def test_07_filter_existing_threads(self):
        saved = [" t1 ", "t2", "t3"]
        current = ["t2", "t3", "t4"]
        out = self.mod.filter_existing_threads(saved, current)
        self.assertEqual(out, ["t2", "t3"])

    # [COMMON-UTILS:T07-01-08] delete_server_data_if_missing: server_id が無ければ json を削除
    def test_08_delete_server_data_if_missing(self):
        p = Path(self.mod.get_server_file_path(self.service, "S1"))
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(["t1"]), encoding="utf-8")
        self.assertTrue(p.exists())

        deleted = self.mod.delete_server_data_if_missing(self.service, "S1", existing_ids={"S2"})
        self.assertTrue(deleted)
        self.assertFalse(p.exists())

        # 既存なら削除しない
        p.write_text(json.dumps(["t1"]), encoding="utf-8")
        deleted2 = self.mod.delete_server_data_if_missing(self.service, "S1", existing_ids={"S1"})
        self.assertFalse(deleted2)
        self.assertTrue(p.exists())

    # [COMMON-UTILS:T07-01-09] clean_deleted_threads: current_ids に無いスレッドは削る
    def test_09_clean_deleted_threads(self):
        self.mod.save_server_threads(self.service, "S1", ["t1", "t2", "t3"])
        self.mod.clean_deleted_threads(self.service, "S1", current_ids=["t2"])
        out = self.mod.load_server_threads(self.service, "S1")
        self.assertEqual(out, ["t2"])

        # 変化がない場合は上書き不要だが、結果が同じであることを確認
        self.mod.clean_deleted_threads(self.service, "S1", current_ids=["t2"])
        out2 = self.mod.load_server_threads(self.service, "S1")
        self.assertEqual(out2, ["t2"])

    # [COMMON-UTILS:T07-01-10] clean_deleted_servers: base_dir 不在なら no-op
    def test_10_clean_deleted_servers_no_base_dir(self):
        base_dir = Path(self.base_dir)
        for f in base_dir.glob("*.json"):
            f.unlink()
        base_dir.rmdir()
        self.mod.clean_deleted_servers(self.service, existing_server_ids=set())

    # [COMMON-UTILS:T07-01-11] clean_deleted_servers: *.json を走査し、存在しない server は削除
    def test_11_clean_deleted_servers_deletes_missing(self):
        # THREADS_DIR 側（get_server_file_path/delete_server_data_if_missing が参照する実体ファイル）は temp に作る
        p1 = Path(self.mod.get_server_file_path(self.service, "S1"))
        p2 = Path(self.mod.get_server_file_path(self.service, "S2"))
        p1.parent.mkdir(parents=True, exist_ok=True)
        p1.write_text("[]", encoding="utf-8")
        p2.write_text("[]", encoding="utf-8")

        # clean_deleted_servers が参照する base_dir は THREADS_DIR ではなく固定 join 経路のため、
        # base_dir だけ「存在する」ことにし、listdir で json 一覧を返す。
        expected_base_dir = str(Path(self.mod.__file__).parent / ".." / ".." / "ui" / self.service / "data" / "threads")
        expected_base_dir = str(Path(expected_base_dir).resolve())

        orig_exists = self.mod.os.path.exists

        def _fake_exists(path: str) -> bool:
            if str(Path(path).resolve()) == expected_base_dir:
                return True
            return orig_exists(path)

        with patch("common.utils.thread_utils.os.path.exists", new=_fake_exists), \
             patch("common.utils.thread_utils.os.listdir", return_value=["S1.json", "S2.json"]):
            self.mod.clean_deleted_servers(self.service, existing_server_ids={"S2"})

        self.assertFalse(p1.exists())
        self.assertTrue(p2.exists())


if __name__ == "__main__":
    mapping: Dict[str, Tuple[str, str]] = {
        "test_01_get_server_file_path": ("COMMON-UTILS:T07-01-01", "get_server_file_path: パス組み立て"),
        "test_02_load_missing_returns_empty": ("COMMON-UTILS:T07-01-02", "load: 未存在 -> []"),
        "test_03_save_and_load_roundtrip": ("COMMON-UTILS:T07-01-03", "save/load: roundtrip + strip"),
        "test_04_add_thread_no_duplicates": ("COMMON-UTILS:T07-01-04", "add: 重複防止"),
        "test_05_remove_thread": ("COMMON-UTILS:T07-01-05", "remove: 存在時のみ削除"),
        "test_06_is_thread_managed": ("COMMON-UTILS:T07-01-06", "is_thread_managed: membership"),
        "test_07_filter_existing_threads": ("COMMON-UTILS:T07-01-07", "filter_existing_threads: フィルタ"),
        "test_08_delete_server_data_if_missing": ("COMMON-UTILS:T07-01-08", "delete_server_data_if_missing: 削除条件"),
        "test_09_clean_deleted_threads": ("COMMON-UTILS:T07-01-09", "clean_deleted_threads: current_ids でクリーン"),
        "test_10_clean_deleted_servers_no_base_dir": ("COMMON-UTILS:T07-01-10", "clean_deleted_servers: base_dir 無し -> return"),
        "test_11_clean_deleted_servers_deletes_missing": ("COMMON-UTILS:T07-01-11", "clean_deleted_servers: 不在server削除"),
    }
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ThreadUtilsTest)
    run_unittest_suite("COMMON-UTILS:T07 common/utils/thread_utils", suite, mapping)
