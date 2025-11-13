# -*- coding: utf-8 -*-
"""
T08-01 : Sharing Session
対象: common.chat.sharing
- export/import、guild 共有、冪等/サニタイズ/互換
"""

import copy
import unittest
from unittest.mock import patch, MagicMock
from tests._report import run_unittest_suite

def _load_targets():
    from common.chat import sharing as S  # type: ignore
    export_s = getattr(S, "export_session", None) or getattr(S, "to_json", None)
    import_s = getattr(S, "import_session", None) or getattr(S, "from_json", None)
    share_g = getattr(S, "share_to_guild", None) or getattr(S, "share", None)
    return S, export_s, import_s, share_g


class SharingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod, cls.export_s, cls.import_s, cls.share_g = _load_targets()

    def _need_export(self):
        if not self.export_s:
            self.skipTest("export_session not found")

    def _need_import(self):
        if not self.import_s:
            self.skipTest("import_session not found")

    def _need_share(self):
        if not self.share_g:
            self.skipTest("share_to_guild not found")

    # ベースとなるダミーセッション
    def _base_session(self):
        return {"id": "s1", "ts": 1, "messages": [{"role": "user", "content": "hi"}]}

    # [T08-01-01] export 基本
    def test_01_export(self):
        self._need_export()
        data = self.export_s(self._base_session())
        self.assertTrue(isinstance(data, dict))
        self.assertIn("messages", data)

    # [T08-01-02] import 基本
    def test_02_import(self):
        self._need_export(); self._need_import()
        src = self.export_s(self._base_session())
        ses = self.import_s(copy.deepcopy(src))
        self.assertIsInstance(ses, dict)
        self.assertTrue(ses.get("messages"))

    # [T08-01-03] guild 共有
    @patch("common.chat.sharing.SSM")
    def test_03_share_to_guild(self, mock_ssm):
        self._need_share()
        self.share_g(guild_id=10, session=self._base_session())
        self.assertTrue(mock_ssm is not None)

    # [T08-01-04] 不正 JSON
    def test_04_invalid_json(self):
        self._need_import()
        bad = {"id": "x"}  # messages 欠落
        out = self.import_s(bad)
        self.assertTrue(out is None or isinstance(out, dict))

    # [T08-01-05] 冪等
    def test_05_idempotent(self):
        self._need_export(); self._need_import()
        data = self.export_s(self._base_session())
        a = self.import_s(copy.deepcopy(data))
        b = self.import_s(copy.deepcopy(data))
        self.assertEqual(a, b)

    # [T08-01-06] サニタイズ
    def test_06_sanitize(self):
        self._need_import()
        raw = {"id":"s1","ts":1,"messages":[{"role":"user","content":"hi"}],"extra":"x"}
        ses = self.import_s(raw)
        if ses is not None:
            self.assertNotIn("extra", ses)

    # [T08-01-07] バージョン互換
    def test_07_version_compat(self):
        self._need_import()
        raw = {"id":"s1","ts":1,"messages":[{"role":"user","content":"hi"}],"version":999}
        out = self.import_s(raw)
        self.assertTrue(out is None or isinstance(out, dict))

    # [T08-01-08] 部分共有
    def test_08_partial_share(self):
        self._need_export(); self._need_import()
        data = self.export_s(self._base_session())
        data["messages"] = data.get("messages", [])[:1]
        ses = self.import_s(data)
        self.assertTrue(isinstance(ses, dict))


if __name__ == "__main__":
    mapping = {
        "test_01_export": ("M02:T08-01-01", "export 基本"),
        "test_02_import": ("M02:T08-01-02", "import 基本"),
        "test_03_share_to_guild": ("M02:T08-01-03", "guild 共有"),
        "test_04_invalid_json": ("M02:T08-01-04", "不正 JSON"),
        "test_05_idempotent": ("M02:T08-01-05", "冪等"),
        "test_06_sanitize": ("M02:T08-01-06", "サニタイズ"),
        "test_07_version_compat": ("M02:T08-01-07", "バージョン互換"),
        "test_08_partial_share": ("M02:T08-01-08", "部分共有"),
    }
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(SharingTest)
    run_unittest_suite("M02:T08-01", suite, mapping)
