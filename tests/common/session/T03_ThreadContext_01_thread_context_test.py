# -*- coding: utf-8 -*-
"""
T03 : ThreadContextManager (common/session/thread_context_manager)

目的:
- ThreadContextManager の基本動作（context/meta/export/injection/jsonable）を単体テストで保証する。
- export_context/export_all はテンポラリへ逃がし、日時は固定して決定的にする。
"""

import json
import os
import unittest
import tempfile
from typing import Dict, Tuple

from tests._report import run_unittest_suite


class ThreadContextManagerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from common.session import thread_context_manager as M  # type: ignore
        cls.mod = M

    def setUp(self):
        self.tcm = self.mod.ThreadContextManager()  # type: ignore[attr-defined]

    # [T03-01-01] get_context: 未存在は []
    def test_01_get_context_default_empty(self):
        out = self.tcm.get_context("t1")
        self.assertEqual(out, [])

    # [T03-01-02] append_context: 添付なしは state="OK"
    def test_02_append_context_no_attachments_sets_ok(self):
        e = self.tcm.append_context(
            thread_id="t1",
            message="user: hi",
            msgid="m1",
            refid=None,
            attachments=None,
        )
        self.assertEqual(e["state"], "OK")
        self.assertEqual(e["msgid"], "m1")
        self.assertEqual(e["refid"], "")
        self.assertEqual(e["attachments"], [])
        self.assertEqual(self.tcm.get_context("t1")[0]["message"], "user: hi")

    # [T03-01-03] append_context: 添付ありは state=""
    def test_03_append_context_with_attachments_sets_pending(self):
        e = self.tcm.append_context(
            thread_id="t1",
            message="user: file",
            msgid="m2",
            refid="r1",
            attachments=[{"name": "a.png"}],
        )
        self.assertEqual(e["state"], "")
        self.assertEqual(e["refid"], "r1")
        self.assertEqual(len(self.tcm.get_context("t1")), 1)

    # [T03-01-04] clear_context/has_context
    def test_04_clear_and_has_context(self):
        self.tcm.append_context("t1", "x", "m1", None, None)
        self.assertTrue(self.tcm.has_context("t1"))
        self.tcm.clear_context("t1")
        self.assertEqual(self.tcm.get_context("t1"), [])
        # 実装どおり：clear してもキーが存在するため True
        self.assertTrue(self.tcm.has_context("t1"))

    # [T03-01-05] get_injection_message: {now_jst} 置換 + tone 追記
    def test_05_get_injection_message_replaces_now_and_appends_tone(self):
        from unittest.mock import patch

        class _FixedDateTime:
            @classmethod
            def now(cls, tz=None):
                import datetime as _dt
                return _dt.datetime(2025, 12, 26, 1, 2, 3, tzinfo=tz)

        auth = {
            "chat": {
                "injection_prompt": "NOW={now_jst}\n",
                "tone_prompt": "TONE=polite\n",
            }
        }
        with patch.object(self.mod, "datetime", _FixedDateTime):
            out = self.tcm.get_injection_message(auth)
        self.assertIn("NOW=2025-12-26 01:02:03 (JST)", out)
        self.assertIn("TONE=polite", out)

    # [T03-01-06] _jsonable: primitives/dict/list/set/other をJSON化可能へ
    def test_06_jsonable_converts_various_types(self):
        class Dummy:
            def __str__(self):
                return "DUMMYOBJ"

        obj = {
            "a": 1,
            "b": True,
            "c": None,
            "d": [1, {"x": 2}],
            "e": set(["s1", "s2"]),
            "f": Dummy(),
        }
        out = self.tcm._jsonable(obj)
        self.assertIsInstance(out, dict)
        self.assertIsInstance(out["d"], list)
        self.assertIsInstance(out["e"], list)  # set -> list
        self.assertEqual(out["f"], "DUMMYOBJ")

        json.dumps(out, ensure_ascii=False)

    # [T03-01-07] export_context: dumpに出力し、payloadの基本構造を満たす
    def test_07_export_context_writes_json(self):
        from unittest.mock import patch

        self.tcm.append_context("th-1", "user: hi", "m1", None, [{"x": 1}])

        with tempfile.TemporaryDirectory() as td:
            def _fake_dirname(_p: str) -> str:
                return td

            class _FixedDateTime:
                @classmethod
                def now(cls, tz=None):
                    import datetime as _dt
                    return _dt.datetime(2025, 12, 26, 12, 34, 56, tzinfo=tz)

            with patch.object(self.mod.os.path, "dirname", new=_fake_dirname), \
                 patch.object(self.mod, "datetime", _FixedDateTime):
                out_path = self.tcm.export_context("th-1")

            self.assertTrue(os.path.isabs(out_path))
            self.assertTrue(os.path.exists(out_path))

            payload = json.loads(open(out_path, "r", encoding="utf-8").read())
            self.assertEqual(payload["thread_id"], "th-1")
            self.assertEqual(payload["count"], 1)
            self.assertIn("exported_at_jst", payload)
            self.assertIsInstance(payload["items"], list)
            self.assertEqual(payload["items"][0]["msgid"], "m1")

    # [T03-01-08] export_all: 例外があっても継続し、成功分だけ返す（exceptのprint行も踏む）
    def test_08_export_all_continues_on_exception(self):
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

            # print をパッチして except 行の到達も明確化（coverageの未実行行対策）
            with patch.object(self.mod.os.path, "dirname", new=_fake_dirname), \
                 patch.object(self.mod, "datetime", _FixedDateTime), \
                 patch.object(self.tcm, "export_context", side_effect=_side_effect), \
                 patch("builtins.print") as _print_mock:
                paths = self.tcm.export_all()

        self.assertEqual(len(paths), 1)
        self.assertTrue(paths[0].endswith("_ok.json"))
        _print_mock.assert_called()  # except の print が呼ばれたこと

    # [T03-01-09] meta: get/set/pop/clear
    def test_09_meta_operations(self):
        self.assertEqual(self.tcm.get_meta("t1", "k", "D"), "D")
        self.tcm.set_meta("t1", "k", 123)
        self.assertEqual(self.tcm.get_meta("t1", "k"), 123)

        v = self.tcm.pop_meta("t1", "k", "X")
        self.assertEqual(v, 123)
        self.assertEqual(self.tcm.get_meta("t1", "k", None), None)

        self.tcm.set_meta("t1", "a", 1)
        self.tcm.set_meta("t1", "b", 2)
        self.tcm.clear_meta("t1", "a")
        self.assertEqual(self.tcm.get_meta("t1", "a", None), None)
        self.assertEqual(self.tcm.get_meta("t1", "b", None), 2)

        self.tcm.clear_meta("t1", None)
        self.assertEqual(self.tcm.get_meta("t1", "b", None), None)

    # [T03-01-10] append_context: 同一threadへ2回追加（初期化ifのFalse側）
    def test_10_append_context_twice_hits_existing_thread_branch(self):
        self.tcm.append_context("t1", "x1", "m1", None, None)
        self.tcm.append_context("t1", "x2", "m2", None, None)
        self.assertEqual(len(self.tcm.get_context("t1")), 2)

    # [T03-01-11] get_injection_message: tone_prompt空 → 追記しない分岐
    def test_11_get_injection_message_without_tone(self):
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

    # [T03-01-12] clear_meta: key不存在分岐 + key削除でdict空→threadごとpop分岐
    def test_12_clear_meta_branches(self):
        # key不存在: 何も起きない
        self.tcm.set_meta("t1", "k1", 1)
        self.tcm.clear_meta("t1", "no_such_key")
        self.assertEqual(self.tcm.get_meta("t1", "k1", None), 1)

        # key削除で空になったら thread_id が meta から除去される分岐
        self.tcm.clear_meta("t1", "k1")
        self.assertEqual(self.tcm.get_meta("t1", "k1", None), None)
        # meta が消えていること（残っていないこと）を間接的に確認
        self.assertEqual(self.tcm.get_meta("t1", "any", "D"), "D")


if __name__ == "__main__":
    mapping: Dict[str, Tuple[str, str]] = {
        "test_01_get_context_default_empty": (
            "COMMON-SESSION:T03-01-01",
            "get_context: 未存在は []",
        ),
        "test_02_append_context_no_attachments_sets_ok": (
            "COMMON-SESSION:T03-01-02",
            "append_context: 添付なしは state='OK'",
        ),
        "test_03_append_context_with_attachments_sets_pending": (
            "COMMON-SESSION:T03-01-03",
            "append_context: 添付ありは state=''（未処理扱い）",
        ),
        "test_04_clear_and_has_context": (
            "COMMON-SESSION:T03-01-04",
            "clear_context/has_context: クリアと存在判定",
        ),
        "test_05_get_injection_message_replaces_now_and_appends_tone": (
            "COMMON-SESSION:T03-01-05",
            "get_injection_message: {now_jst} 置換 + tone 追記",
        ),
        "test_06_jsonable_converts_various_types": (
            "COMMON-SESSION:T03-01-06",
            "_jsonable: UI依存型を含む構造をJSON化可能へ整形",
        ),
        "test_07_export_context_writes_json": (
            "COMMON-SESSION:T03-01-07",
            "export_context: dumpへJSON出力（構造確認）",
        ),
        "test_08_export_all_continues_on_exception": (
            "COMMON-SESSION:T03-01-08",
            "export_all: 例外があっても継続し成功分のみ返す（except print到達）",
        ),
        "test_09_meta_operations": (
            "COMMON-SESSION:T03-01-09",
            "meta: get/set/pop/clear の基本動作",
        ),
        "test_10_append_context_twice_hits_existing_thread_branch": (
            "COMMON-SESSION:T03-01-10",
            "append_context: 同一threadへ2回追加（初期化ifのFalse側）",
        ),
        "test_11_get_injection_message_without_tone": (
            "COMMON-SESSION:T03-01-11",
            "get_injection_message: tone_prompt空なら追記しない",
        ),
        "test_12_clear_meta_branches": (
            "COMMON-SESSION:T03-01-12",
            "clear_meta: key不存在分岐 + key削除でdict空→meta.pop分岐",
        ),
    }

    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ThreadContextManagerTest)
    run_unittest_suite("COMMON-SESSION:T03 common/session/thread_context_manager", suite, mapping)
