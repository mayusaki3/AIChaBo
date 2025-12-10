# -*- coding: utf-8 -*-
"""
T08-02 : Sharing Migration
対象: common.chat.sharing
- 旧フォーマットから現行セッション形式への移行（migration）とフォールバック挙動を検証
"""

import unittest
from typing import Any, Dict
from tests._report import run_unittest_suite


class SharingMigrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # テスト対象モジュールを一度だけ import
        from common.chat import sharing as S  # type: ignore
        cls.mod = S

    # 旧形式: history キーのみ・version 無し
    def _legacy_history_dict(self) -> Dict[str, Any]:
        return {
            "provider": "openai",
            "model": "gpt-4o",
            # 旧形式では messages ではなく history を使っていた想定
            "history": [
                {"role": "user", "content": "hello"},
                {"role": "assistant", "content": "world"},
            ],
        }

    # 旧形式: version=0 + history
    def _legacy_v0_json(self) -> str:
        return (
            '{"version": 0, '
            '"provider": "openai", '
            '"model": "gpt-4o", '
            '"history": ['
            '{"role":"user","content":"hello"},'
            '{"role":"assistant","content":"world"}'
            ']}'
        )

    # [T08-02-01] 旧形式 dict 入力のマイグレーション
    def test_01_legacy_dict_migration(self):
        src = self._legacy_history_dict()

        # dict をそのまま渡しても import_session が受け取れる前提
        ses = self.mod.import_session(src)  # type: ignore[arg-type]

        # provider/model は維持される
        self.assertEqual(ses.get("provider"), "openai")
        self.assertEqual(ses.get("model"), "gpt-4o")

        # history → messages へのマッピングが行われていること
        msgs = ses.get("messages")
        self.assertIsInstance(msgs, list)
        self.assertGreaterEqual(len(msgs), 2)
        self.assertEqual(msgs[0].get("role"), "user")
        self.assertEqual(msgs[0].get("content"), "hello")

        # version は数値で 1 以上になっている想定
        ver = ses.get("version")
        self.assertIsInstance(ver, int)
        self.assertGreaterEqual(ver, 1)

    # [T08-02-02] 旧形式 JSON(v0) のマイグレーション
    def test_02_legacy_v0_json_migration(self):
        raw = self._legacy_v0_json()

        ses = self.mod.import_session(raw)

        self.assertEqual(ses.get("provider"), "openai")
        self.assertEqual(ses.get("model"), "gpt-4o")

        msgs = ses.get("messages")
        self.assertIsInstance(msgs, list)
        self.assertGreaterEqual(len(msgs), 2)

        # version=0 → 1 以上に補正されていること
        ver = ses.get("version")
        self.assertIsInstance(ver, int)
        self.assertGreaterEqual(ver, 1)

    # [T08-02-03] 余剰フィールド付き旧形式のサニタイズ
    def test_03_legacy_with_extra_fields_sanitized(self):
        src = {
            "provider": "openai",
            "model": "gpt-4o",
            "history": [{"role": "user", "content": "hi"}],
            # 旧形式やデバッグで付いていたかもしれないフィールド
            "unknown": "xxx",
            "token_count": 123,
            "last_used": 999999,
        }

        ses = self.mod.import_session(src)  # type: ignore[arg-type]

        # 必須フィールドは残る
        self.assertEqual(ses.get("provider"), "openai")
        self.assertEqual(ses.get("model"), "gpt-4o")
        self.assertIsInstance(ses.get("messages"), list)

        # 余剰フィールドは落ちていること
        self.assertNotIn("unknown", ses)
        self.assertNotIn("token_count", ses)
        self.assertNotIn("last_used", ses)

    # [T08-02-04] version 型不整合のフォールバック
    def test_04_invalid_version_type_fallback(self):
        raw = {
            "version": "legacy",  # 不正な型
            "provider": "openai",
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": "hi"}],
        }

        ses = self.mod.import_session(raw)  # type: ignore[arg-type]

        # provider/model/messages はそのまま有効
        self.assertEqual(ses.get("provider"), "openai")
        self.assertEqual(ses.get("model"), "gpt-4o")
        self.assertIsInstance(ses.get("messages"), list)

        # version は数値化される or version 未指定扱いとして 1 以上の数値に正規化される想定
        ver = ses.get("version")
        self.assertIsInstance(ver, int)
        self.assertGreaterEqual(ver, 1)

    # [T08-02-05] dict 直接入力の互換性
    def test_05_dict_with_messages_passthrough(self):
        src = {
            # version 無しだが messages は現行形式
            "provider": "openai",
            "model": "gpt-4o",
            "messages": [
                {"role": "user", "content": "hello"},
            ],
        }

        ses = self.mod.import_session(src)  # type: ignore[arg-type]

        # ほぼそのまま、足りないフィールドだけ補完される想定
        self.assertEqual(ses.get("provider"), "openai")
        self.assertEqual(ses.get("model"), "gpt-4o")
        msgs = ses.get("messages")
        self.assertIsInstance(msgs, list)
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0].get("content"), "hello")

        # version 補完確認
        ver = ses.get("version")
        self.assertIsInstance(ver, int)
        self.assertGreaterEqual(ver, 1)


if __name__ == "__main__":
    mapping = {
        "test_01_legacy_dict_migration": (
            "M02:T08-02-01",
            "旧形式 dict 入力のマイグレーション",
        ),
        "test_02_legacy_v0_json_migration": (
            "M02:T08-02-02",
            "旧形式 JSON(v0) のマイグレーション",
        ),
        "test_03_legacy_with_extra_fields_sanitized": (
            "M02:T08-02-03",
            "余剰フィールド付き旧形式のサニタイズ",
        ),
        "test_04_invalid_version_type_fallback": (
            "M02:T08-02-04",
            "version 型不整合のフォールバック",
        ),
        "test_05_dict_with_messages_passthrough": (
            "M02:T08-02-05",
            "dict 直接入力の互換性",
        ),
    }
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(SharingMigrationTest)
    run_unittest_suite("M02:T08-02 common/chat/sharing migration", suite, mapping)
