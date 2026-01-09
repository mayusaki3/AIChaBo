# tests/common/session/T03_thread_context_02impl_thread_context_test.py
# -*- coding: utf-8 -*-
"""
COMMON-SESSION:T03-02 : ThreadContextManager（TCM）impl/branch テスト（カバレッジ目的）

対象: common/session/thread_context_manager.py
"""

from __future__ import annotations

import os
import tempfile
import unittest
from typing import Dict, Tuple

from tests._report import run_unittest_suite


class ThreadContextManagerImplTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from common.session import thread_context_manager as M  # type: ignore
        cls.mod = M

    def setUp(self):
        self.tcm = self.mod.ThreadContextManager()  # type: ignore[attr-defined]

    # [COMMON-SESSION:T03-02-01] append_context: 同一threadへ2回追加（初期化ifのFalse側）
    def test_01_append_context_twice_hits_existing_thread_branch(self):
        self.tcm.append_context("t1", "x1", "m1", None, None)
        self.tcm.append_context("t1", "x2", "m2", None, None)
        self.assertEqual(len(self.tcm.get_context("t1")), 2)

    # [COMMON-SESSION:T03-02-02] get_injection_message: tone_prompt空 → 追記しない分岐
    def test_02_get_injection_message_without_tone(self):
        from unittest.mock import patch

        class _FixedDateTime:
            @classmethod
            def now(cls, tz=None):
                import datetime as _dt
                return _dt.datetime(2025, 12, 26, 1, 2, 3, tzinfo=tz)

        auth = {"chat": {"injection_prompt": "NOW={now_jst}\n", "tone_prompt": ""}}
        with patch.object(self.mod, "datetime", _FixedDateTime):
            out = self.tcm.get_injection_message(auth)
        self.assertIn("NOW=2025-12-26 01:02:03 (JST)", out)
        self.assertNotIn("TONE=", out)

    # [COMMON-SESSION:T03-02-03] export_all: 例外があっても継続し成功分だけ返す（except print到達）
    def test_03_export_all_continues_on_exception(self):
        from unittest.mock import patch

        self.tcm.append_context("ok", "x", "m1", None, None)
        self.tcm.append_context("ng", "y", "m2", None, None)

        original_export = self.tcm.export_context

        def _side_effect(thread_id: str) -> str:
            if str(thread_id) == "ng":
                raise RuntimeError("boom")
            return original_export(thread_id)

        with tempfile.TemporaryDirectory() as td:
            def _fake_dirname(_p: str) -> str:
                return td

            class _FixedDateTime:
                @classmethod
                def now(cls, tz=None):
                    import datetime as _dt
                    return _dt.datetime(2025, 12, 26, 0, 0, 0, tzinfo=tz)

            with patch.object(self.mod.os.path, "dirname", new=_fake_dirname), \
                 patch.object(self.mod, "datetime", _FixedDateTime), \
                 patch.object(self.tcm, "export_context", side_effect=_side_effect), \
                 patch("builtins.print") as _print_mock:
                paths = self.tcm.export_all()

        self.assertEqual(len(paths), 1)
        self.assertTrue(paths[0].endswith("_ok.json"))
        _print_mock.assert_called()

    # [COMMON-SESSION:T03-02-04] clear_meta: key不存在分岐 + key削除でdict空→meta.pop分岐
    def test_04_clear_meta_branches(self):
        # key不存在: 何も起きない
        self.tcm.set_meta("t1", "k1", 1)
        self.tcm.clear_meta("t1", "no_such_key")
        self.assertEqual(self.tcm.get_meta("t1", "k1", None), 1)

        # key削除で空になったら thread_id が meta から除去される
        self.tcm.clear_meta("t1", "k1")
        self.assertEqual(self.tcm.get_meta("t1", "k1", None), None)
        self.assertEqual(self.tcm.get_meta("t1", "any", "D"), "D")


mapping: Dict[str, Tuple[str, str]] = {
    "test_01_append_context_twice_hits_existing_thread_branch": ("COMMON-SESSION:T03-02-01", "append_context: 同一threadへ2回追加（初期化if False）"),
    "test_02_get_injection_message_without_tone": ("COMMON-SESSION:T03-02-02", "get_injection_message: tone_prompt空なら追記しない"),
    "test_03_export_all_continues_on_exception": ("COMMON-SESSION:T03-02-03", "export_all: 例外があっても継続（except print到達）"),
    "test_04_clear_meta_branches": ("COMMON-SESSION:T03-02-04", "clear_meta: key不存在分岐 + dict空→meta.pop分岐"),
}

if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ThreadContextManagerImplTest)
    run_unittest_suite("COMMON-SESSION:T03-02 (impl) common/session/thread_context_manager", suite, mapping)
