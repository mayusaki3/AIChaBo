# -*- coding: utf-8 -*-
"""
T08-02 : Sharing Session Migration
対象: common.chat.sharing

目的:
- 旧形式（dict直入力 / v0 JSON など）を import_session で受けられる互換層を検証する
- 余剰フィールドが混在しても安全にサニタイズされること
- version 型不整合でも落ちずにフォールバックすること
"""

import json
import unittest
from typing import Any, Dict, List

from tests._report import run_unittest_suite


class SharingMigrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from common.chat import sharing as S  # type: ignore
        cls.mod = S

    # [T08-02-01] 旧形式 dict 入力のマイグレーション
    def test_01_legacy_dict_migration(self):
        # 旧形式想定: provider/model/messages が揃っている dict
        src: Dict[str, Any] = {
            "provider": "openai",
            "model": "gpt-4o",
            "messages": [
                {"role": "user", "content": "hello"},
                {"role": "assistant", "content": "world"},
            ],
        }

        ses = self.mod.import_session(src)  # type: ignore[arg-type]
        self.assertIsInstance(ses, dict)
        self.assertEqual(ses.get("provider"), "openai")
        self.assertEqual(ses.get("model"), "gpt-4o")

        msgs = ses.get("messages")
        self.assertIsInstance(msgs, list)

    # [T08-02-02] 旧形式 JSON(v0) のマイグレーション
    def test_02_legacy_v0_json_migration(self):
        # v0 想定: "version":0 か version 欠落 + messages が旧構造でも落ちないこと
        raw = json.dumps(
            {
                "version": 0,
                "provider": "openai",
                "model": "gpt-4o",
                "messages": [
                    {"role": "user", "content": "a"},
                    {"role": "assistant", "content": "b"},
                ],
            }
        )

        ses = self.mod.import_session(raw)
        self.assertIsInstance(ses, dict)

        msgs = ses.get("messages")
        self.assertIsInstance(msgs, list)
        self.assertGreaterEqual(len(msgs), 2)

    # [T08-02-03] 余剰フィールド付き旧形式のサニタイズ
    def test_03_legacy_with_extra_fields_sanitized(self):
        src: Dict[str, Any] = {
            "version": 0,
            "provider": "openai",
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": "hi"}],
            "unknown": "xxx",
            "tokens": 999,
        }

        ses = self.mod.import_session(src)  # type: ignore[arg-type]
        self.assertIsInstance(ses, dict)
        self.assertEqual(ses.get("provider"), "openai")
        self.assertEqual(ses.get("model"), "gpt-4o")

        # 余剰キーが落ちる想定（少なくとも unknown が残らない）
        self.assertNotIn("unknown", ses)

    # [T08-02-04] version 型不整合のフォールバック
    def test_04_invalid_version_type_fallback(self):
        # version が str 等でも落ちない
        src: Dict[str, Any] = {
            "version": "1",  # 型不整合
            "provider": "openai",
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": "hi"}],
        }

        ses = self.mod.import_session(src)  # type: ignore[arg-type]
        self.assertIsInstance(ses, dict)
        self.assertEqual(ses.get("provider"), "openai")
        self.assertEqual(ses.get("model"), "gpt-4o")

    # [T08-02-05] dict 直接入力の互換性（messages ありの passthrough 系）
    def test_05_dict_with_messages_passthrough(self):
        src: Dict[str, Any] = {
            "version": 1,
            "provider": "openai",
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": "ok"}],
        }

        ses = self.mod.import_session(src)  # type: ignore[arg-type]
        self.assertIsInstance(ses, dict)
        self.assertEqual(ses.get("provider"), "openai")
        self.assertEqual(ses.get("model"), "gpt-4o")
        self.assertEqual(ses.get("messages"), src["messages"])


if __name__ == "__main__":
    mapping = {
        "test_01_legacy_dict_migration": ("COMMON-CHAT:T08-02-01", "旧形式 dict 入力のマイグレーション"),
        "test_02_legacy_v0_json_migration": ("COMMON-CHAT:T08-02-02", "旧形式 JSON(v0) のマイグレーション"),
        "test_03_legacy_with_extra_fields_sanitized": ("COMMON-CHAT:T08-02-03", "余剰フィールド付き旧形式のサニタイズ"),
        "test_04_invalid_version_type_fallback": ("COMMON-CHAT:T08-02-04", "version 型不整合のフォールバック"),
        "test_05_dict_with_messages_passthrough": ("COMMON-CHAT:T08-02-05", "dict 直接入力の互換性"),
    }
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(SharingMigrationTest)
    run_unittest_suite("COMMON-CHAT:T08-02 common/chat/sharing migration", suite, mapping)
