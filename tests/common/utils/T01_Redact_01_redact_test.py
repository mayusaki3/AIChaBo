# -*- coding: utf-8 -*-
"""
COMMON-UTILS:T01 : redact

対象: common.utils.redact

目的:
- 機密っぽいトークンをログ出力前にマスクできること
- prefix+value 形式 / 値単体形式の両方の分岐を網羅
- keep 引数の反映、非文字列入力の安全性を確認

重要:
- 関数を class attribute に入れると bound method 化し self が混入することがあるため、
  staticmethod で保持して “常に生関数として呼ぶ”。
"""

import unittest
from typing import Dict, Tuple

from tests._report import run_unittest_suite


class RedactTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from common.utils.redact import redact  # type: ignore
        cls.redact_fn = staticmethod(redact)  # ← bound method 化の完全回避

    def _redact(self, s, keep=4):
        # staticmethod 化したものを “関数” として呼ぶ
        return self.__class__.redact_fn(s, keep)

    # [COMMON-UTILS:T01-01-01] api_key= 形式（prefix+value）マスク
    def test_01_api_key_prefix_value_mask(self):
        s = "api_key=ABCDEFGH12345678"
        out = self._redact(s)
        self.assertEqual(out, "api_key=***")

    # [COMMON-UTILS:T01-01-02] API-KEY: 形式（prefix+value）マスク（大小無視）
    def test_02_api_key_dash_colon_mask(self):
        s = "API-KEY: ABCDEFGH12345678"
        out = self._redact(s)
        self.assertEqual(out, "API-KEY: ***")

    # [COMMON-UTILS:T01-01-03] sk- 形式（値のみ一致）マスク
    def test_03_sk_value_only_mask(self):
        s = "token=sk-ABCDEFGH12345678"
        out = self._redact(s, keep=4)
        self.assertEqual(out, "token=sk-A***")

    # [COMMON-UTILS:T01-01-04] ghp_ 形式（値のみ一致）マスク
    def test_04_ghp_value_only_mask(self):
        s = "gh=ghp_0123456789ABCDEFGHIJKLMNOP"
        out = self._redact(s, keep=4)
        self.assertEqual(out, "gh=ghp_***")

    # [COMMON-UTILS:T01-01-05] AIza 形式（値のみ一致）マスク
    def test_05_aiza_value_only_mask(self):
        s = "AIzaSyDUMMY0123456789ABCDEFGH"
        out = self._redact(s, keep=4)
        self.assertEqual(out, "AIza***")

    # [COMMON-UTILS:T01-01-06] keep 指定の反映（値のみ一致）
    def test_06_keep_parameter(self):
        s = "sk-ABCDEFGH12345678"
        out = self._redact(s, keep=2)
        self.assertEqual(out, "sk***")

    # [COMMON-UTILS:T01-01-07] 非文字列入力の安全性
    def test_07_non_string_input(self):
        out = self._redact(12345)
        self.assertEqual(out, "12345")

    # [COMMON-UTILS:T01-01-08] 非一致は不変
    def test_08_no_match_unchanged(self):
        s = "hello world"
        out = self._redact(s)
        self.assertEqual(out, s)


if __name__ == "__main__":
    mapping: Dict[str, Tuple[str, str]] = {
        "test_01_api_key_prefix_value_mask": ("COMMON-UTILS:T01-01-01", "api_key= 形式（prefix+value）マスク"),
        "test_02_api_key_dash_colon_mask": ("COMMON-UTILS:T01-01-02", "API-KEY: 形式（prefix+value）マスク"),
        "test_03_sk_value_only_mask": ("COMMON-UTILS:T01-01-03", "sk- 形式（値のみ一致）マスク"),
        "test_04_ghp_value_only_mask": ("COMMON-UTILS:T01-01-04", "ghp_ 形式（値のみ一致）マスク"),
        "test_05_aiza_value_only_mask": ("COMMON-UTILS:T01-01-05", "AIza 形式（値のみ一致）マスク"),
        "test_06_keep_parameter": ("COMMON-UTILS:T01-01-06", "keep 指定の反映（値のみ一致）"),
        "test_07_non_string_input": ("COMMON-UTILS:T01-01-07", "非文字列入力の安全性"),
        "test_08_no_match_unchanged": ("COMMON-UTILS:T01-01-08", "非一致は不変"),
    }
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(RedactTest)
    run_unittest_suite("COMMON-UTILS:T01 common/utils/redact", suite, mapping)
