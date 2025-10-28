# -*- coding: utf-8 -*-
"""
provider_test.py
- provider名の正規化/表示名の単体テスト（I/Oなし・常時実行可）
  実行:  python -m utiltests.provider_test
"""
import unittest

from common.chat.provider import normalize_provider, display_provider


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
        # 未知はそのまま返す方針
        self.assertEqual(display_provider("somenewllm"), "somenewllm")


if __name__ == "__main__":
    unittest.main()
