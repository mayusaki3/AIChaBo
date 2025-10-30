# -*- coding: utf-8 -*-
"""
T01_Provider_01_provider_test.py
目的: プロバイダ名の正規化/表示名の単体テスト（I/Oなし・常時実行可）
実行例: python -m utiltests.T01_Provider_01_provider_test
"""
import unittest
from common.chat.provider import normalize_provider, display_provider
from utiltests._report import run_unittest_suite

class ProviderTest(unittest.TestCase):
    def test_normalize_known(self):
        self.assertEqual(normalize_provider("OpenAI"), "openai")
        self.assertEqual(normalize_provider("openai"), "openai")
        self.assertEqual(normalize_provider("gpt"), "openai")
        self.assertEqual(normalize_provider("Anthropic"), "claude")
        self.assertEqual(normalize_provider("claude"), "claude")
        self.assertEqual(normalize_provider("Google"), "gemini")
        self.assertEqual(normalize_provider("gemini"), "gemini")

    def test_normalize_unknown(self):
        self.assertEqual(normalize_provider("SomeNewLLM"), "somenewllm")
        self.assertEqual(normalize_provider(""), "")

    def test_display(self):
        self.assertEqual(display_provider("openai"), "OpenAI")
        self.assertEqual(display_provider("claude"), "Claude")
        self.assertEqual(display_provider("gemini"), "Gemini")
        self.assertEqual(display_provider("somenewllm"), "somenewllm")  # 未知はそのまま

if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ProviderTest)
    mapping = {
        "test_normalize_known":   ("T01-01-01", "normalize known"),
        "test_normalize_unknown": ("T01-01-02", "normalize unknown"),
        "test_display":           ("T01-01-03", "display names"),
    }
    run_unittest_suite("T01-01", suite, mapping)
