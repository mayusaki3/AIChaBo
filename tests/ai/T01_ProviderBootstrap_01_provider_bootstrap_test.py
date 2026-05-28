# -*- coding: utf-8 -*-
"""
AI:T01-01 Provider Bootstrap 単体テスト
目的:
  - 標準 provider adapter が Provider Adapter Registry に登録されることを確認する。
  - reload 失敗時に registry 状態が復元されることを確認する。
  - bootstrap が API キーや外部 API 呼び出しを要求しないことを確認する。
実行例:
  python -m tests.ai.T01_ProviderBootstrap_01_provider_bootstrap_test
出力:
  ✅/❌ と [AI:T01-01-xx] を先頭に持つ行 + SUMMARY（共通レポータ）
"""

import unittest
from unittest import mock

from tests._report import run_unittest_suite
from common.chat import provider_registry as registry
from ai import provider_bootstrap


async def _sentinel_adapter(context_list, api_key, model, **options):
    """役割: 復元確認用の sentinel adapter。"""
    return "sentinel"


class ProviderBootstrapTest(unittest.TestCase):
    """Provider bootstrap の公開 API と registry 連携を検証する。"""

    def setUp(self):
        """各テスト開始時に registry 状態を退避し、空状態へ初期化する。"""
        self._snapshot = registry.snapshot_providers()
        registry.clear_providers()

    def tearDown(self):
        """各テスト終了時に registry 状態を復元し、テスト間の状態漏洩を防ぐ。"""
        registry.restore_providers(self._snapshot)

    # [AI:T01-01-01] 標準 provider key 一覧:
    #   登録対象 provider が固定順で返ること。
    def test_01_standard_provider_keys(self):
        self.assertEqual(
            provider_bootstrap.get_standard_provider_keys(),
            ["openai", "gemini", "claude"],
        )

    # [AI:T01-01-02] 標準 provider 登録:
    #   OpenAI / Gemini / Claude が registry に登録されること。
    def test_02_register_standard_providers(self):
        provider_bootstrap.register_standard_providers()
        self.assertEqual(registry.list_providers(), ["openai", "gemini", "claude"])
        self.assertTrue(registry.has_provider("openai"))
        self.assertTrue(registry.has_provider("gemini"))
        self.assertTrue(registry.has_provider("claude"))

    # [AI:T01-01-03] overwrite=False の重複登録:
    #   既に登録済みの場合、標準登録の再実行は拒否されること。
    def test_03_register_standard_providers_duplicate_rejected(self):
        provider_bootstrap.register_standard_providers()
        with self.assertRaises(ValueError):
            provider_bootstrap.register_standard_providers()

    # [AI:T01-01-04] overwrite=True の再登録:
    #   明示上書きにより標準 provider を再登録できること。
    def test_04_register_standard_providers_overwrite(self):
        provider_bootstrap.register_standard_providers()
        provider_bootstrap.register_standard_providers(overwrite=True)
        self.assertEqual(registry.list_providers(), ["openai", "gemini", "claude"])

    # [AI:T01-01-05] reload 成功:
    #   registry を標準 provider のみで再構成できること。
    def test_05_reload_standard_providers_success(self):
        registry.register_provider("localtest", _sentinel_adapter)
        provider_bootstrap.reload_standard_providers()
        self.assertEqual(registry.list_providers(), ["openai", "gemini", "claude"])

    # [AI:T01-01-06] reload 失敗時の復元:
    #   登録処理が失敗した場合、直前の registry 状態へ復元されること。
    def test_06_reload_standard_providers_restore_on_failure(self):
        registry.register_provider("localtest", _sentinel_adapter)
        before = registry.snapshot_providers()

        with mock.patch.object(provider_bootstrap, "register_standard_providers", side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                provider_bootstrap.reload_standard_providers()

        self.assertEqual(registry.list_providers(), list(before.keys()))
        self.assertIs(registry.resolve_provider("localtest"), _sentinel_adapter)

    # [AI:T01-01-07] APIキー不要:
    #   bootstrap は API キー引数や環境変数を要求せず登録のみを行うこと。
    def test_07_bootstrap_does_not_require_api_key(self):
        provider_bootstrap.register_standard_providers()
        for provider in provider_bootstrap.get_standard_provider_keys():
            self.assertTrue(registry.has_provider(provider))


if __name__ == "__main__":
    mapping = {
        "test_01_standard_provider_keys": ("AI:T01-01-01", "standard provider keys"),
        "test_02_register_standard_providers": ("AI:T01-01-02", "register standard providers"),
        "test_03_register_standard_providers_duplicate_rejected": ("AI:T01-01-03", "duplicate rejected"),
        "test_04_register_standard_providers_overwrite": ("AI:T01-01-04", "overwrite standard providers"),
        "test_05_reload_standard_providers_success": ("AI:T01-01-05", "reload success"),
        "test_06_reload_standard_providers_restore_on_failure": ("AI:T01-01-06", "reload restore on failure"),
        "test_07_bootstrap_does_not_require_api_key": ("AI:T01-01-07", "no api key required"),
    }
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ProviderBootstrapTest)
    run_unittest_suite("AI:T01-01 ai/provider_bootstrap", suite, mapping)
