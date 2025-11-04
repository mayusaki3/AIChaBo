# -*- coding: utf-8 -*-
"""
T01_Provider_01_provider_test.py
目的: プロバイダ名の正規化/表示名の単体検証（I/Oなし・常時実行可）
実行例: python -m utiltests.T01_Provider_01_provider_test
"""
import unittest
from common.chat.provider import normalize_provider, display_provider
from utiltests._report import run_unittest_suite

class ProviderTest(unittest.TestCase):
    def test_01_normalize_known(self):
        """既知エイリアスの正規化"""
        self.assertEqual(normalize_provider("OpenAI"), "openai")
        self.assertEqual(normalize_provider("openai"), "openai")
        self.assertEqual(normalize_provider("gpt"), "openai")
        self.assertEqual(normalize_provider("Anthropic"), "claude")
        self.assertEqual(normalize_provider("claude"), "claude")
        self.assertEqual(normalize_provider("Google"), "gemini")
        self.assertEqual(normalize_provider("gemini"), "gemini")

    def test_02_normalize_unknown(self):
        """未知名称の扱い（小文字化のみ）"""
        self.assertEqual(normalize_provider("SomeNewLLM"), "somenewllm")
        self.assertEqual(normalize_provider(""), "")

    def test_03_display(self):
        """表示名のマッピング"""
        self.assertEqual(display_provider("openai"), "OpenAI")
        self.assertEqual(display_provider("claude"), "Claude")
        self.assertEqual(display_provider("gemini"), "Gemini")
        # 未知はそのまま表示
        self.assertEqual(display_provider("somenewllm"), "somenewllm")

    def test_04_display_empty(self):
        """空/非文字列入力の扱い（display_provider の早期return分岐を踏む）"""
        self.assertEqual(display_provider(""), "")
        # 非文字列は normalize_provider 側では弾く想定だが、display_provider への直通防御も確認
        self.assertEqual(display_provider(None), "")

if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ProviderTest)
    mapping = {
        "test_01_normalize_known":   ("T01-01-01", "normalize known"),
        "test_02_normalize_unknown": ("T01-01-02", "normalize unknown"),
        "test_03_display":           ("T01-01-03", "display names"),
        "test_04_display_empty":     ("T01-01-04", "display empty"),
    }
    run_unittest_suite("T01-01", suite, mapping)
