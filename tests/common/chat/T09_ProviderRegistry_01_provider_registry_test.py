# -*- coding: utf-8 -*-
"""
COMMON-CHAT:T09-01 Provider Adapter Registry 単体テスト
目的:
  - provider adapter の登録、解決、重複登録、snapshot/restore、clear が仕様どおり動作することを確認する。
  - 外部 AI API を呼ばず、テスト用 adapter のみで registry 経路を検証する。
実行例:
  python -m tests.common.chat.T09_ProviderRegistry_01_provider_registry_test
出力:
  ✅/❌ と [COMMON-CHAT:T09-01-xx] を先頭に持つ行 + SUMMARY（共通レポータ）
"""

import unittest

from tests._report import run_unittest_suite
from common.chat import provider_registry as registry


async def _mock_success_adapter(context_list, api_key, model, **options):
    """役割: 正常応答を返すテスト用 provider adapter。"""
    return f"mock:{model}:{len(context_list or [])}"


async def _mock_second_adapter(context_list, api_key, model, **options):
    """役割: 上書き確認用の別 adapter。"""
    return "mock-second"


class ProviderRegistryTest(unittest.TestCase):
    """Provider Adapter Registry の公開 API を検証する。"""

    def setUp(self):
        """各テスト開始時に registry 状態を退避し、空状態へ初期化する。"""
        self._snapshot = registry.snapshot_providers()
        registry.clear_providers()

    def tearDown(self):
        """各テスト終了時に registry 状態を復元し、テスト間の状態漏洩を防ぐ。"""
        registry.restore_providers(self._snapshot)

    # [COMMON-CHAT:T09-01-01] provider adapter 登録:
    #   正規化済み provider key と adapter を登録できること。
    def test_01_register_provider(self):
        registry.register_provider("openai", _mock_success_adapter)
        self.assertTrue(registry.has_provider("openai"))
        self.assertIn("openai", registry.list_providers())

    # [COMMON-CHAT:T09-01-02] provider key 正規化:
    #   OpenAI などの別名入力でも正規化済み key として保持されること。
    def test_02_register_normalizes_provider_key(self):
        registry.register_provider("OpenAI", _mock_success_adapter)
        self.assertTrue(registry.has_provider("openai"))
        self.assertTrue(registry.has_provider("gpt"))
        self.assertEqual(registry.list_providers(), ["openai"])

    # [COMMON-CHAT:T09-01-03] provider adapter 解決:
    #   登録済み provider key から同一 adapter を取得できること。
    def test_03_resolve_provider(self):
        registry.register_provider("gemini", _mock_success_adapter)
        self.assertIs(registry.resolve_provider("gemini"), _mock_success_adapter)
        self.assertIs(registry.resolve_provider("Google"), _mock_success_adapter)

    # [COMMON-CHAT:T09-01-04] 未登録 provider:
    #   未登録 provider 解決時は明示的な KeyError になること。
    def test_04_unregistered_provider_raises(self):
        with self.assertRaises(KeyError):
            registry.resolve_provider("unknown")

    # [COMMON-CHAT:T09-01-05] 重複登録禁止:
    #   overwrite=False では同一 provider key の重複登録を拒否すること。
    def test_05_duplicate_registration_rejected(self):
        registry.register_provider("claude", _mock_success_adapter)
        with self.assertRaises(ValueError):
            registry.register_provider("claude", _mock_second_adapter)
        self.assertIs(registry.resolve_provider("claude"), _mock_success_adapter)

    # [COMMON-CHAT:T09-01-06] 明示上書き:
    #   overwrite=True の場合のみ adapter を差し替えられること。
    def test_06_duplicate_registration_overwrite(self):
        registry.register_provider("claude", _mock_success_adapter)
        registry.register_provider("claude", _mock_second_adapter, overwrite=True)
        self.assertIs(registry.resolve_provider("claude"), _mock_second_adapter)

    # [COMMON-CHAT:T09-01-07] adapter callable 検証:
    #   callable でない値の登録を拒否すること。
    def test_07_reject_non_callable_adapter(self):
        with self.assertRaises(TypeError):
            registry.register_provider("openai", object())

    # [COMMON-CHAT:T09-01-08] provider 空入力ガード:
    #   空 provider 名の登録・解決を拒否すること。
    def test_08_reject_empty_provider(self):
        with self.assertRaises(ValueError):
            registry.register_provider("   ", _mock_success_adapter)
        with self.assertRaises(ValueError):
            registry.resolve_provider("   ")

    # [COMMON-CHAT:T09-01-09] snapshot/restore:
    #   registry 状態を退避し、変更後に元へ復元できること。
    def test_09_snapshot_restore(self):
        registry.register_provider("openai", _mock_success_adapter)
        snapshot = registry.snapshot_providers()

        registry.clear_providers()
        registry.register_provider("gemini", _mock_second_adapter)
        self.assertEqual(registry.list_providers(), ["gemini"])

        registry.restore_providers(snapshot)
        self.assertEqual(registry.list_providers(), ["openai"])
        self.assertIs(registry.resolve_provider("openai"), _mock_success_adapter)

    # [COMMON-CHAT:T09-01-10] clear:
    #   clear_providers により registry が空になること。
    def test_10_clear_providers(self):
        registry.register_provider("openai", _mock_success_adapter)
        registry.register_provider("gemini", _mock_second_adapter)
        registry.clear_providers()
        self.assertEqual(registry.list_providers(), [])
        self.assertFalse(registry.has_provider("openai"))


if __name__ == "__main__":
    mapping = {
        "test_01_register_provider": ("COMMON-CHAT:T09-01-01", "register provider"),
        "test_02_register_normalizes_provider_key": ("COMMON-CHAT:T09-01-02", "normalize provider key"),
        "test_03_resolve_provider": ("COMMON-CHAT:T09-01-03", "resolve provider"),
        "test_04_unregistered_provider_raises": ("COMMON-CHAT:T09-01-04", "unregistered provider"),
        "test_05_duplicate_registration_rejected": ("COMMON-CHAT:T09-01-05", "duplicate registration rejected"),
        "test_06_duplicate_registration_overwrite": ("COMMON-CHAT:T09-01-06", "duplicate registration overwrite"),
        "test_07_reject_non_callable_adapter": ("COMMON-CHAT:T09-01-07", "reject non callable adapter"),
        "test_08_reject_empty_provider": ("COMMON-CHAT:T09-01-08", "reject empty provider"),
        "test_09_snapshot_restore": ("COMMON-CHAT:T09-01-09", "snapshot restore"),
        "test_10_clear_providers": ("COMMON-CHAT:T09-01-10", "clear providers"),
    }
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ProviderRegistryTest)
    run_unittest_suite("COMMON-CHAT:T09-01 common/chat/provider_registry", suite, mapping)
