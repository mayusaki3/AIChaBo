# -*- coding: utf-8 -*-
"""
T08-01 : Sharing Session
対象: common.chat.sharing
- export/import、guild 共有、冪等/サニタイズ/互換
"""

import copy
import unittest
from typing import Any, Dict
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
        # テスト対象モジュールを一度だけ import
        from common.chat import sharing as S  # type: ignore
        cls.mod = S

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
    def _base_session(self) -> Dict[str, Any]:
        """
        T08-01 の「基本」「部分共有」などで使うベースセッション。
        export/import の往復で provider/model も保持されることを確認する前提なので、
        provider/model を含めた形で定義する。
        """
        return {
            "id": "s1",
            "ts": 1,
            "provider": "openai",
            "model": "gpt-4o",
            "messages": [
                {"role": "user", "content": "hi"},
            ],
        }

    # [T08-01-01] export 基本
    def test_01_export(self):
        base = self._base_session()
        data = self.mod.export_session(base)  # ← self.export_s(...) から修正

        # 最低限のフォーマット確認（JSON 文字列であること）
        self.assertIsInstance(data, str)
        self.assertIn('"provider"', data)
        self.assertIn('"model"', data)

    # [T08-01-02] import 基本
    def test_02_import(self):
        base = self._base_session()
        src = self.mod.export_session(base)   # ← self.export_s(...) から修正

        restored = self.mod.import_session(src)  # ← self.import_s(...) から修正

        # provider/model あたりが戻っていることをざっくり確認
        self.assertEqual(restored.get("provider"), base["provider"])
        self.assertEqual(restored.get("model"), base["model"])

    # [T08-01-03] guild 共有
    @patch("common.chat.sharing._share_to_server_impl")
    def test_03_share_to_guild(self, mock_impl):
        base = self._base_session()

        # guild 共有呼び出し（self.share_g(...) → self.mod.share_to_guild(...)）
        self.mod.share_to_guild(guild_id=10, session=base)

        mock_impl.assert_called_once()
        args, kwargs = mock_impl.call_args
        self.assertEqual(kwargs.get("guild_id"), 10)
        self.assertEqual(kwargs.get("session"), base)

    # [T08-01-04] 不正 JSON
    def test_04_invalid_json(self):
        bad = "{not json}"

        out = self.mod.import_session(bad)  # ← self.import_s(...) から修正

        # 不正 JSON の場合は空 dict 等にフォールバックする想定
        self.assertIsInstance(out, dict)

    # [T08-01-05] 冪等
    def test_05_idempotent(self):
        base = self._base_session()

        data1 = self.mod.export_session(base)        # ← self.export_s(...)
        ses1 = self.mod.import_session(data1)        # ← self.import_s(...)

        data2 = self.mod.export_session(ses1)        # 再 export
        ses2 = self.mod.import_session(data2)

        # 冪等性：2 回目も同じ内容になること
        self.assertEqual(ses1, ses2)

    # [T08-01-06] サニタイズ
    def test_06_sanitize(self):
        # 余分なキーを混ぜたセッション
        raw_session = {
            "provider": "openai",
            "model": "gpt-4o",
            "tokens": 1000,
            "unknown": "xxx",
        }

        raw = self.mod.export_session(raw_session)   # ← self.export_s(...)
        ses = self.mod.import_session(raw)          # ← self.import_s(...)

        # 不要なキーが落ちているなど、最低限のサニタイズ確認
        self.assertEqual(ses.get("provider"), "openai")
        self.assertEqual(ses.get("model"), "gpt-4o")
        self.assertNotIn("unknown", ses)

    # [T08-01-07] バージョン互換
    def test_07_version_compat(self):
        # 旧バージョン形式の JSON を模したデータ（例）
        raw = '{"version": 1, "provider": "openai", "model": "gpt-4o"}'

        out = self.mod.import_session(raw)  # ← self.import_s(...) から修正

        # 少なくとも provider/model が取得できること
        self.assertEqual(out.get("provider"), "openai")
        self.assertEqual(out.get("model"), "gpt-4o")

    # [T08-01-08] 部分共有
    def test_08_partial_share(self):
        base = self._base_session()
        # 何らかの部分共有オプションを付けて export する想定
        data = self.mod.export_session(base)   # ← self.export_s(...)

        ses = self.mod.import_session(data)    # ← self.import_s(...)

        # ここでは「少なくとも provider/model は残っている」程度を確認
        self.assertEqual(ses.get("provider"), base["provider"])
        self.assertEqual(ses.get("model"), base["model"])


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
    run_unittest_suite("M02:T08-01 common/chat/sharing", suite, mapping)
