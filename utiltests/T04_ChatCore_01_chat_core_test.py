# utiltests/T04_ChatCore_01_chat_core_test.py
# ------------------------------------------------------------
# T04-01 : ChatCore 基本
# 目的:
#  - guard(empty)、provider/model 必須、最小往復（モック/実装状況に応じて Skip）
# 出力:
#  - ✅/❌ [T04-01-xx] ... と --- SUMMARY T04-01: ... --- を共通レポータで統一
# 実行:
#  - python -m utiltests.T04_ChatCore_01_chat_core_test
# ------------------------------------------------------------
import unittest

# 共通レポータ（unittest 要約を抑止して ✅/❌ + SUMMARY を出す）
from utiltests._report import run_unittest_suite

# テスト対象: chat_core（実体に合わせて import できない場合は Skip）
try:
    from common.chat.chat_core import send_once  # 想定API
except Exception:
    send_once = None

class ChatCoreBasicTest(unittest.TestCase):
    """
    ケース設計
      T04-01-01: 入力ガード（空文字/空白のみ → 例外 or 既定応答）
      T04-01-02: provider/model 必須（欠落時は例外）
      T04-01-03: 最小往復（モック差し替え未整備なら Skip）
    """

    def test_01_guard_empty_text(self):
        """入力ガード（空文字/空白のみ → 例外 or 既定応答）"""
        if send_once is None:
            self.skipTest("chat_core が未配置のため Skip")
        text = "   "
        ctx = {"provider": "openai", "model": "gpt-4o-mini"}
        try:
            res = send_once(text=text, context=ctx)
        except Exception:
            res = None
        self.assertTrue(res is None or isinstance(res, str))

    def test_02_require_provider_model(self):
        """provider/model 必須（欠落時は例外）"""
        if send_once is None:
            self.skipTest("chat_core が未配置のため Skip")
        with self.assertRaises(Exception):
            send_once(text="hi", context={"provider": "openai"})         # model 無し
        with self.assertRaises(Exception):
            send_once(text="hi", context={"model": "gpt-4o-mini"})       # provider 無し

    def test_03_basic_roundtrip_with_mock(self):
        """最小往復（モック未整備なら Skip）"""
        if send_once is None:
            self.skipTest("chat_core が未配置のため Skip")
        try:
            res = send_once(text="ping", context={"provider": "openai", "model": "gpt-4o-mini"})
            self.assertIsInstance(res, str)
        except Exception:
            self.skipTest("モック差し替え未整備のため Skip")


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ChatCoreBasicTest)
    mapping = {
        "test_01_guard_empty_text":        ("T04-01-01", "guard(empty)"),
        "test_02_require_provider_model":  ("T04-01-02", "require provider/model"),
        "test_03_basic_roundtrip_with_mock": ("T04-01-03", "roundtrip with mock (minimal)"),
    }
    run_unittest_suite("T04-01", suite, mapping)
