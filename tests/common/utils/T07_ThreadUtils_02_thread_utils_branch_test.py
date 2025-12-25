# -*- coding: utf-8 -*-
"""
COMMON-UTILS:T07-02 : thread_utils branch

目的:
- thread_utils の分岐網羅（branch coverage）を上げる
"""

import unittest
from typing import Dict, Tuple
from unittest.mock import patch

from tests._report import run_unittest_suite


class ThreadUtilsBranchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from common.utils import thread_utils as mod  # type: ignore
        cls.mod = mod

    # [COMMON-UTILS:T07-02-01] clean_deleted_threads: filtered==saved なら save しない分岐
    def test_01_clean_deleted_threads_no_change_does_not_save(self):
        with patch("common.utils.thread_utils.load_server_threads", return_value=["t1", "t2"]), \
             patch("common.utils.thread_utils.filter_existing_threads", return_value=["t1", "t2"]), \
             patch("common.utils.thread_utils.save_server_threads") as save_mock:
            self.mod.clean_deleted_threads("discord", "S1", current_ids=["t1", "t2"])
            save_mock.assert_not_called()

    # [COMMON-UTILS:T07-02-02] delete_server_data_if_missing: file無 → False（exists False 側）
    def test_02_delete_server_data_if_missing_when_file_not_exists_returns_false(self):
        with patch("common.utils.thread_utils.get_server_file_path", return_value="X:/nope.json"), \
             patch("common.utils.thread_utils.os.path.exists", return_value=False), \
             patch("common.utils.thread_utils.os.remove") as rm_mock:
            ok = self.mod.delete_server_data_if_missing("discord", "S1", existing_ids=set())
            self.assertFalse(ok)
            rm_mock.assert_not_called()

    # [COMMON-UTILS:T07-02-03] delete_server_data_if_missing: server_id既存 → False（削除しない側）
    def test_03_delete_server_data_if_missing_when_server_exists_returns_false(self):
        with patch("common.utils.thread_utils.get_server_file_path", return_value="X:/exists.json"), \
             patch("common.utils.thread_utils.os.path.exists", return_value=True), \
             patch("common.utils.thread_utils.os.remove") as rm_mock:
            ok = self.mod.delete_server_data_if_missing("discord", "S1", existing_ids={"S1"})
            self.assertFalse(ok)
            rm_mock.assert_not_called()

    # [COMMON-UTILS:T07-02-04] clean_deleted_servers: *.json 以外は無視（endswith False 側 → 78->77）
    def test_04_clean_deleted_servers_ignores_non_json_files(self):
        # base_dir が存在し、listdir に .json 以外が混ざっているケース
        with patch("common.utils.thread_utils.os.path.exists", return_value=True), \
             patch("common.utils.thread_utils.os.listdir", return_value=["note.txt"]), \
             patch("common.utils.thread_utils.delete_server_data_if_missing") as del_mock:
            self.mod.clean_deleted_servers("discord", existing_server_ids=set())
            del_mock.assert_not_called()


if __name__ == "__main__":
    mapping: Dict[str, Tuple[str, str]] = {
        "test_01_clean_deleted_threads_no_change_does_not_save": (
            "COMMON-UTILS:T07-02-01",
            "clean_deleted_threads: filtered==saved なら save しない分岐",
        ),
        "test_02_delete_server_data_if_missing_when_file_not_exists_returns_false": (
            "COMMON-UTILS:T07-02-02",
            "delete_server_data_if_missing: file無 → False（exists False 側）",
        ),
        "test_03_delete_server_data_if_missing_when_server_exists_returns_false": (
            "COMMON-UTILS:T07-02-03",
            "delete_server_data_if_missing: server_id既存 → False（削除しない側）",
        ),
        "test_04_clean_deleted_servers_ignores_non_json_files": (
            "COMMON-UTILS:T07-02-04",
            "clean_deleted_servers: *.json 以外は無視（endswith False 側）",
        ),
    }

    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ThreadUtilsBranchTest)
    run_unittest_suite("COMMON-UTILS:T07-02 common/utils/thread_utils branch", suite, mapping)
