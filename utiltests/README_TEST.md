# utiltests/T05_ChatLoop_01_chat_loop_test.py
# ------------------------------------------------------------
# T05-01 : ChatLoop 基本
# 目的:
#  - 空入力の振る舞い（"（入力が空です）"）の固定化
#  - provider/model 欠落時のガイダンス文言（現行仕様）確認
# 出力:
#  - ✅/❌ [T05-01-xx] ... と --- SUMMARY T05-01: ... --- を共通レポータで統一
# 実行:
#  - python -m utiltests.T05_ChatLoop_01_chat_loop_test
# ------------------------------------------------------------
import unittest

# 共通レポータ（unittest 要約を抑止して ✅/❌ + SUMMARY を出す）
from utiltests._report import run_unittest_suite

# テスト対象: chat_loop（現行版）
try:
    from common.chat.chat_loop import chat_loop
except Exception:
    chat_loop = None  # 未配置でもスイート自体は動かせるようにする

class ChatLoopBasicTest(unittest.TestCase):
    """
    ケース設計
      T05-01-01: 空入力 → 固定文言 "（入力が空です）"
      T05-01-02: provider/model 欠落時 → ガイダンス文言（現行仕様）
    """

    def test_01_empty_input_returns_fixed_message(self):
        """空入力 → "（入力が空です）" を返す"""
        if chat_loop is None:
            self.skipTest("chat_loop が未配置のため Skip")
        out = chat_loop(user_text="  ", context={"provider": "openai", "model": "gpt-4o-mini"})
        self.assertEqual(out, "（入力が空です）")

    def test_02_missing_provider_or_model(self):
        """provider/model 欠落時のガイダンス文言（現行仕様）"""
        if chat_loop is None:
            self.skipTest("chat_loop が未配置のため Skip")
        msg1 = chat_loop(user_text="hi", context={"provider": "openai"})       # model 無し
        msg2 = chat_loop(user_text="hi", context={"model": "gpt-4o-mini"})     # provider 無し
        self.assertIsInstance(msg1, str)
        self.assertIsInstance(msg2, str)
        # 例: "（モデル設定が見つかりません。/ac_auth で設定してください）"
        self.assertIn("モデル設定", msg1)
        self.assertIn("モデル設定", msg2)


if __name__ == "__main__":
    # unittest スイートを Reporter で実行（番号とタイトルを対応付け）
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ChatLoopBasicTest)
    mapping = {
        # method_name: (test_id, title)
        "test_01_empty_input_returns_fixed_message": ("T05-01-01", "empty -> fixed message"),
        "test_02_missing_provider_or_model":         ("T05-01-02", "missing provider/model -> guidance"),
    }
    run_unittest_suite("T05-01", suite, mapping)
