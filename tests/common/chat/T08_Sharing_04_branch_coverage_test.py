# tests/common/chat/T08_Sharing_04_branch_coverage_test.py
import unittest
from common.chat import sharing


class T08_Sharing_04_BranchCoverageTest(unittest.TestCase):

    def test_01_export_empty_dict(self):
        out = sharing.export_session({})
        self.assertIsInstance(out, str)

    def test_02_export_non_dict(self):
        self.assertIsInstance(sharing.export_session([]), str)
        self.assertIsInstance(sharing.export_session("x"), str)

    def test_03_import_unknown_version(self):
        raw = '{"version": 999, "messages": []}'
        ses = sharing.import_session(raw)
        self.assertIsInstance(ses, dict)

    def test_04_import_messages_not_list(self):
        raw = '{"version": 1, "messages": "oops"}'
        ses = sharing.import_session(raw)
        self.assertEqual(ses.get("messages"), [])

    def test_05_migrate_legacy_empty_messages(self):
        legacy = {"id": "s", "ts": 1}
        ses = sharing.import_session(legacy)
        self.assertIn("messages", ses)

    def test_06_share_noop_impl(self):
        # 内部実装未定義でも例外が出ないこと
        sharing.share_to_guild(guild_id=1, session={})


if __name__ == "__main__":
    unittest.main()
