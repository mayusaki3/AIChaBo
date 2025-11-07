# -*- coding: utf-8 -*-
"""
T01-01 Provider 正規化・表示名テスト
目的:
  - provider 名の正規化 (normalize) と表示名変換 (display) が
    既知/未知/空入力の各パスで正しく動作することを確認する。
実行例:
  python -m tests.T01_Provider_01_provider_test
出力:
  ✅/❌ と [T01-01-xx] を先頭に持つ行 + SUMMARY（共通レポータ）
"""

import unittest

from tests._report import run_unittest_suite  # 共通の結果レポータ
from common.chat.provider import (
    normalize_provider,  # 入力 → 正規化ID（小文字, 既知エイリアスは canonical へ）
    display_provider,    # 正規化ID → 表示名（例: "openai" → "OpenAI"）
)


class ProviderTest(unittest.TestCase):
    """
    - unittest はメソッド名の昇順で実行されるため、順序固定のため test_01_*, test_02_* ... と連番を付与
    - ここでは I/O は発生せず、純粋関数をテストする
    """

    # [T01-01-01] 既知名称/エイリアスの正規化:
    #   入力が "OpenAI" や alias（例: "gpt"）でも "openai" に正規化されること
    def test_01_normalize_known(self):
        self.assertEqual(normalize_provider("OpenAI"), "openai")
        self.assertEqual(normalize_provider("openai"), "openai")
        # alias の例（実装側で alias→canonical にしている想定）
        self.assertEqual(normalize_provider("gpt"), "openai")
        self.assertEqual(normalize_provider("Anthropic"), "claude")
        self.assertEqual(normalize_provider("claude"), "claude")
        self.assertEqual(normalize_provider("Google"), "gemini")
        self.assertEqual(normalize_provider("gemini"), "gemini")

    # [T01-01-02] 未知名称の扱い:
    #   未知の provider は小文字化のみ（例外にはしない）
    def test_02_normalize_unknown(self):
        self.assertEqual(normalize_provider("SomeNewLLM"), "somenewllm")
        self.assertEqual(normalize_provider(""), "")          # 空文字は空のまま
        self.assertEqual(normalize_provider(None), "")        # None 等の非文字列も空扱い

    # [T01-01-03] 表示名:
    #   正規化済みID（"openai"）を表示名（"OpenAI"）に変換
    def test_03_display_names(self):
        self.assertEqual(display_provider("openai"), "OpenAI")
        self.assertEqual(display_provider("claude"), "Claude")
        self.assertEqual(display_provider("gemini"), "Gemini")
        # 未知はそのまま表示
        self.assertEqual(display_provider("somenewllm"), "somenewllm")

    # [T01-01-04] 表示名: 空系
    #   "" や None を与えた場合の安全な返却（空文字など）
    def test_04_display_empty(self):
        self.assertEqual(display_provider(""), "")
        self.assertEqual(display_provider(None), "")


if __name__ == "__main__":
    # メソッド名と [Txx-yy-zz] のひも付け（表示用タイトル）
    mapping = {
        "test_01_normalize_known":  ("T01-01-01", "normalize known"),
        "test_02_normalize_unknown":("T01-01-02", "normalize unknown"),
        "test_03_display_names":    ("T01-01-03", "display names"),
        "test_04_display_empty":    ("T01-01-04", "display empty"),
    }
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ProviderTest)
    run_unittest_suite("T01-01", suite, mapping)
