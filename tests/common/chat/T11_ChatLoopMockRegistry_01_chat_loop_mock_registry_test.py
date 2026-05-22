# -*- coding: utf-8 -*-
"""
COMMON-CHAT:T11-01 chat_loop registry-based mock テスト
目的:
  - registry-based mock provider により chat_loop の provider 経路を検証する。
  - 外部 AI API を呼ばずに正常系・例外系・未登録 provider を確認する。
  - adapter 例外時に UI 向け安全メッセージへ変換されることを確認する。
実行例:
  python -m tests.common.chat.T11_ChatLoopMockRegistry_01_chat_loop_mock_registry_test
出力:
  ✅/❌ と [COMMON-CHAT:T11-01-xx] を先頭に持つ行 + SUMMARY（共通レポータ）
"""

from __future__ import annotations

import unittest
from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch

from tests._report import run_unittest_suite
from common.chat import provider_registry as registry
from common.chat import chat_loop


async def _success_mock_adapter(context_list, api_key, model, **options):
    """役割: 正常応答を返す registry-based mock adapter。"""
    return f"mock-success:{model}:{len(context_list)}"


async def _error_mock_adapter(context_list, api_key, model, **options):
    """役割: provider adapter 例外を再現する mock adapter。"""
    raise RuntimeError("mock provider failure")


async def _secret_leak_mock_adapter(context_list, api_key, model, **options):
    """役割: 機密情報混入例外を再現する mock adapter。"""
    raise RuntimeError("API_KEY=sk-test-secret-123")


class ChatLoopMockRegistryTest(IsolatedAsyncioTestCase):
    """registry-based mock provider による chat_loop の動作を検証する。"""

    def setUp(self):
        """registry 状態を退避し、テスト用状態へ初期化する。"""
        self._snapshot = registry.snapshot_providers()
        registry.clear_providers()

    def tearDown(self):
        """registry 状態を復元し、テスト間漏洩を防ぐ。"""
        registry.restore_providers(self._snapshot)

    def _patch_policy_and_key(self):
        """chat_loop の policy/key 解決をテスト固定値へ差し替える。"""
        return patch.multiple(
            chat_loop,
            _extract_chat_policy_from_sessions=lambda **kwargs: {
                "model": "mock-model",
                "max_tokens": 128,
            },
            _resolve_api_key=lambda **kwargs: "dummy-api-key",
        )

    # [COMMON-CHAT:T11-01-01] registry-based mock success:
    #   registry 登録済み mock adapter で chat_loop が成功すること。
    async def test_01_chat_loop_success_with_registry_mock(self):
        registry.register_provider("openai", _success_mock_adapter)

        with self._patch_policy_and_key():
            result = await chat_loop.run(
                provider="openai",
                context_list=["hello"],
                user_id=1,
                guild_id=100,
            )

        self.assertEqual(result, "mock-success:mock-model:1")

    # [COMMON-CHAT:T11-01-02] unregistered provider:
    #   未登録 provider の場合、安全なエラーメッセージになること。
    async def test_02_chat_loop_unregistered_provider(self):
        with self._patch_policy_and_key():
            result = await chat_loop.run(
                provider="unknown",
                context_list=["hello"],
                user_id=1,
                guild_id=100,
            )

        self.assertEqual(result, "（チャット実行でエラーが発生しました）")

    # [COMMON-CHAT:T11-01-03] provider adapter failure:
    #   adapter 内部例外が UI 向け安全メッセージへ変換されること。
    async def test_03_chat_loop_provider_failure(self):
        registry.register_provider("openai", _error_mock_adapter)

        with self._patch_policy_and_key():
            result = await chat_loop.run(
                provider="openai",
                context_list=["hello"],
                user_id=1,
                guild_id=100,
            )

        self.assertEqual(result, "（チャット実行でエラーが発生しました）")

    # [COMMON-CHAT:T11-01-04] secret leak protection:
    #   adapter 例外に機密情報が含まれても UI 応答へ露出しないこと。
    async def test_04_chat_loop_secret_leak_protection(self):
        registry.register_provider("openai", _secret_leak_mock_adapter)

        with self._patch_policy_and_key():
            result = await chat_loop.run(
                provider="openai",
                context_list=["hello"],
                user_id=1,
                guild_id=100,
            )

        self.assertEqual(result, "（チャット実行でエラーが発生しました）")
        self.assertNotIn("sk-test-secret", result)


if __name__ == "__main__":
    mapping = {
        "test_01_chat_loop_success_with_registry_mock": (
            "COMMON-CHAT:T11-01-01",
            "registry mock success",
        ),
        "test_02_chat_loop_unregistered_provider": (
            "COMMON-CHAT:T11-01-02",
            "unregistered provider",
        ),
        "test_03_chat_loop_provider_failure": (
            "COMMON-CHAT:T11-01-03",
            "provider adapter failure",
        ),
        "test_04_chat_loop_secret_leak_protection": (
            "COMMON-CHAT:T11-01-04",
            "secret leak protection",
        ),
    }

    suite = unittest.defaultTestLoader.loadTestsFromTestCase(
        ChatLoopMockRegistryTest
    )

    run_unittest_suite(
        "COMMON-CHAT:T11-01 chat_loop registry-based mock",
        suite,
        mapping,
    )
