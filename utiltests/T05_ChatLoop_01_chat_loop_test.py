# utiltests/chat_loop_test.py  — コメント付き完全版
# 目的:
# - .envtest の有無に応じて MOCK/REAL を切り替えて実行バナーを表示
# - テスト時のモデル名は「事前に seed した USM の非機密メタ」から取得
# - chat_loop.run(...) は位置引数で呼び出し（本番の実体シグネチャに追従）
# - .envtest が無い（=MOCK）場合は、test_helpers.seed_mock_for_provider() が
#   SecretStore と USM に対して鍵/メタを投入する前提

import asyncio
import os
from utiltests.test_helpers import (
    TEST_USER_ID,
    TEST_GUILD_ID,
    load_envtest,            # .envtest 読み込み（無ければ MOCK）
    banner_print_env,        # 実行モードのバナー表示
    seed_mock_for_provider,  # MOCK 用：鍵と非機密メタを投入
    cleanup_secret_keys,     # テスト後に鍵をクリア
)
from common.session.user_session_manager import user_session_manager as USM
from common.chat import chat_loop

# プロバイダ別の安全デフォルト（USM にモデルが無い場合のバックアップ）
DEFAULT_MODELS = {
    "openai":     "gpt-4o-mini",
    "anthropic":  "claude-3-5-sonnet-latest",
    "google":     "gemini-1.5-pro",
}

def _get_model_from_usm_or_default(provider: str) -> str:
    """USM に seed 済みの非機密メタからモデル名を引く。無ければ安全デフォルト。"""
    try:
        sess = USM.get_session(TEST_USER_ID) or {}
        auth = (sess.get("auth") or {}).get(provider) or {}
        model = auth.get("model")
        if isinstance(model, str) and model.strip():
            return model.strip()
    except Exception:
        pass
    return DEFAULT_MODELS.get(provider, "gpt-4o-mini")

async def run_one(provider: str, prompt: str) -> str:
    # ここでモデル名は「テスト投入済みの USM の非機密メタ」から取得する
    model = _get_model_from_usm_or_default(provider)
    # chat_loop.run のシグネチャ（位置引数）に合わせる:
    # async def run(provider: str, model: str, context_list: list[str], user_id: int, guild_id: int) -> str
    return await chat_loop.run(
        provider,              # 1: provider
        model,                 # 2: model（USM またはデフォルト）
        ["mock", prompt],      # 3: context_list（MOCK 指示）
        TEST_USER_ID,          # 4: user_id
        TEST_GUILD_ID,         # 5: guild_id
    )

async def main():
    # 1) .envtest 読み込み & モード判定
    env = load_envtest()
    banner_print_env(env)

    # 2) MOCK モードなら、全プロバイダの鍵＆非機密メタを seed
    is_mock = env.get("MODE") == "MOCK"
    providers = ("openai", "anthropic", "google")
    if is_mock:
        for p in providers:
            # 非機密メタには model="mock" を入れておく（無視されても OK）
            seed_mock_for_provider(p, model="mock", shared=False)

    # 3) 各プロバイダを最小 1 回ずつ実行
    for p in providers:
        try:
            out = await run_one(p, "please return short echo for test")
            print(f"[{p}] -> {out}")
        except TypeError as te:
            print(f"[{p}] -> (ERROR: {te})")
        except Exception as e:
            print(f"[{p}] -> (ERROR: {e})")

    # 4) 後始末（鍵のクリーンアップ）
    #    REAL モードの場合は .envtest で投入した実 API キーが使われるので削除
    for p in providers:
        try:
            cleanup_secret_keys(p)
        except Exception:
            pass

if __name__ == "__main__":
    asyncio.run(main())
