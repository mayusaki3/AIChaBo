# -*- coding: utf-8 -*-
"""
COMMON-UTILS:T04 : file_io

対象: common.utils.file_io

目的:
- parse_auth_file() が UTF-8 JSON を正しく dict に復元できること
- JSON パース失敗時に {"error": "..."} を返すこと
- UTF-8 decode 失敗時にも {"error": "..."} を返すこと
- 入力が bytes でない場合でも例外を投げず {"error": "..."} を返すこと（型ガード）

テスト番号:
- COMMON-UTILS:T04-01-01 ...（T04=file_io, 01=テストコード, 01..=ケース）

実行:
- python -m tests.common.utils.T04_FileIo_01_file_io_test
"""

import json
import unittest
from typing import Any, Dict, Tuple

from tests._report import run_unittest_suite


class FileIoTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from common.utils import file_io as mod  # type: ignore
        cls.mod = mod

    # [COMMON-UTILS:T04-01-01] 正常: UTF-8 JSON bytes -> dict
    def test_01_parse_auth_file_valid_json(self):
        payload = {"provider": "openai", "model": "gpt", "x": 1}
        b = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        out = self.mod.parse_auth_file(b)
        self.assertEqual(out, payload)

    # [COMMON-UTILS:T04-01-02] 異常: JSON として不正 -> {"error": "..."}
    def test_02_parse_auth_file_invalid_json_returns_error(self):
        b = b"{ not json"
        out = self.mod.parse_auth_file(b)
        self.assertIsInstance(out, dict)
        self.assertIn("error", out)
        self.assertIsInstance(out["error"], str)
        self.assertTrue(len(out["error"]) > 0)

    # [COMMON-UTILS:T04-01-03] 異常: UTF-8 decode 失敗 -> {"error": "..."}
    def test_03_parse_auth_file_invalid_utf8_returns_error(self):
        # 0xFF は UTF-8 として不正になりやすい
        b = bytes([0xFF, 0xFE, 0xFD])
        out = self.mod.parse_auth_file(b)
        self.assertIsInstance(out, dict)
        self.assertIn("error", out)
        self.assertIsInstance(out["error"], str)
        self.assertTrue(len(out["error"]) > 0)

    # [COMMON-UTILS:T04-01-04] 異常: bytes 以外 -> {"error": "..."}（例外を外に出さない）
    def test_04_parse_auth_file_non_bytes_returns_error(self):
        out = self.mod.parse_auth_file("not-bytes")  # type: ignore[arg-type]
        self.assertIsInstance(out, dict)
        self.assertIn("error", out)
        self.assertIsInstance(out["error"], str)
        self.assertTrue(len(out["error"]) > 0)


if __name__ == "__main__":
    mapping: Dict[str, Tuple[str, str]] = {
        "test_01_parse_auth_file_valid_json": ("COMMON-UTILS:T04-01-01", "parse_auth_file: 正常 JSON bytes"),
        "test_02_parse_auth_file_invalid_json_returns_error": ("COMMON-UTILS:T04-01-02", "parse_auth_file: 不正 JSON -> error"),
        "test_03_parse_auth_file_invalid_utf8_returns_error": ("COMMON-UTILS:T04-01-03", "parse_auth_file: 不正 UTF-8 -> error"),
        "test_04_parse_auth_file_non_bytes_returns_error": ("COMMON-UTILS:T04-01-04", "parse_auth_file: bytes 以外 -> error"),
    }
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(FileIoTest)
    run_unittest_suite("COMMON-UTILS:T04 common/utils/file_io", suite, mapping)
