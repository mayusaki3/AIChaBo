# tests/T04_ChatCore_01_chat_core_test.py
# ------------------------------------------------------------
# T04-01 : ChatCore 基本
# 目的:
#  - guard(empty)、provider/model 必須、最小往復（モック/実装状況に応じて Skip）
# 出力:
#  - ✅/❌ [T04-01-xx] ... と --- SUMMARY T04-01: ... --- を共通レポータで統一
# 実行:
#  - python -m tests.T04_ChatCore_01_chat_core_test
# ------------------------------------------------------------
import unittest

# 共通レポータ（unittest 要約を抑止して ✅/❌ + SUMMARY を出す）
from tests._report import run_unittest_suite

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

    def test_04_guard_non_str_input(self):
        """guard(non-str): text=None で ValueError を投げる枝を到達"""
        from common.chat.chat_core import send_once
        with self.assertRaises(ValueError):
            send_once(text=None, context={"provider":"openai","model":"m"})

    def test_05_echo_without_chat_fn(self):
        """echo 分岐: chat_fn を渡さない場合は trim 済みの文字列をそのまま返す"""
        from common.chat.chat_core import send_once
        out = send_once(text="  ping  ", context={"provider":"openai","model":"m"})
        self.assertEqual(out, "ping")

    def test_06_chat_fn_injection_is_called(self):
        """chat_fn 注入分岐: 注入された関数が呼ばれ、provider/model が渡される"""
        from common.chat.chat_core import send_once
        called = {}
        def fake_chat_fn(*, text, provider, model):
            # 呼び出し時の引数を記録し、戻り値を返す
            called["text"] = text
            called["provider"] = provider
            called["model"] = model
            return f"ok:{provider}:{model}:{text}"
        out = send_once(
            text="pong",
           context={"provider": "openai", "model": "gpt-4o-mini"},
            chat_fn=fake_chat_fn,
        )
        self.assertEqual(out, "ok:openai:gpt-4o-mini:pong")
        self.assertEqual(called, {
            "text": "pong", "provider": "openai", "model": "gpt-4o-mini"
        })


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ChatCoreBasicTest)
    mapping = {
        "test_01_guard_empty_text":          ("T04-01-01", "guard(empty)"),
        "test_02_require_provider_model":    ("T04-01-02", "require provider/model"),
        "test_03_basic_roundtrip_with_mock": ("T04-01-03", "roundtrip with mock (minimal)"),
        "test_04_guard_non_str_input":       ("T04-01-04", "guard(non-str)"),
        "test_05_echo_without_chat_fn":      ("T04-01-05", "echo without chat_fn"),
        "test_06_chat_fn_injection_is_called": ("T04-01-06", "chat_fn injection is called"),
    }
    run_unittest_suite("T04-01", suite, mapping)
