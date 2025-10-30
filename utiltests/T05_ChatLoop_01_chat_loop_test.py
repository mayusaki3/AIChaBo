# -*- coding: utf-8 -*-
"""
T05_ChatLoop_01_chat_loop_test.py
目的: chat_loop.run の最小パス検証（.envtest 無し=MOCK想定）
実行例: python -m utiltests.T05_ChatLoop_01_chat_loop_test
"""
import asyncio
from utiltests.test_helpers import (
    TEST_USER_ID,
    TEST_GUILD_ID,
    load_envtest,            # .envtest 読み込み（無い場合は MOCK 想定）
    banner_print_env,        # 実行モードの表示
    seed_mock_for_provider,  # MOCK: 秘密鍵・非機密モデルを投入
    cleanup_secret_keys,     # テスト後に鍵クリア
)
from common.chat import chat_loop
from utiltests._report import make_reporter

DEFAULT_MODELS = {
    "openai":    "gpt-4o-mini",
    "anthropic": "claude-3-5-sonnet-latest",
    "google":    "gemini-1.5-pro",
}

async def run_one(provider: str, prompt: str, model: str | None = None) -> str:
    """chat_loop.run を1回だけ実行。model 未指定ならデフォルトを使用。"""
    mdl = model or DEFAULT_MODELS.get(provider, "gpt-4o-mini")
    # chat_loop.run(provider, context_list, user_id, guild_id, model=None)
    return await chat_loop.run(
        provider,
        ["\\s mock system", prompt],
        TEST_USER_ID,
        TEST_GUILD_ID,
        mdl,
    )

async def main():
    env = load_envtest()
    banner_print_env(env)
    rep = make_reporter("T05-01")
    rep.banner("ChatLoop basic")

    is_mock = env.get("MODE") == "MOCK"
    providers = ("openai", "anthropic", "google")
    if is_mock:
        for p in providers:
            seed_mock_for_provider(p, model=DEFAULT_MODELS[p], shared=False)

    for p in providers:
        with rep.case(f"{p} echo"):
            out = await run_one(p, "please return short echo for test")
            assert isinstance(out, str) and len(out) > 0, "empty response"

    for p in providers:
        try:
            cleanup_secret_keys(p)
        except Exception:
            pass
    rep.summary()

if __name__ == "__main__":
    asyncio.run(main())
