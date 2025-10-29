# utiltests/chat_loop_test.py
# コメント: .envtest の有無で実鍵/モックを自動切替。存在するプロバイダだけテスト。
import os, asyncio
from utiltests._secrets import seed, cleanup, OPENAI_KEY, CLAUDE_KEY, GEMINI_KEY, TEST_USER_ID, TEST_GUILD_ID
from common.chat import chat_loop

from dotenv import load_dotenv, find_dotenv
if not load_dotenv(dotenv_path=".envtest"):
    os.environ["AIChaBo_TEST_MOCK"] = "1"  # .envtest 無→モックON

async def run_one(provider: str, text: str):
    from utiltests.test_helpers import build_min_context_for_test
    # テスト用コンテキスト（provider/model 等を内包）
    ctx = build_min_context_for_test(provider=provider)
    # 実行：chat_loop が APIキー/モデルを内部解決
    out = await chat_loop.run(
        user_text=text,
        context=ctx,
    )
    print(f"[{provider}] -> {out[:120]}")

async def main():
    seed()
    try:
        if os.getenv("AIChaBo_TEST_MOCK") == "1":
            # モック用の指示（「mock, …」を含む context を渡すための入力文字列）
            await run_one("openai", "mock, please return short echo for test")
            await run_one("anthropic", "mock, speak as BOT for unit-test")
            await run_one("google", "mock, reply with OK:g")
        else:
            if OPENAI_KEY:
                await run_one("openai", "Hello from test")
            else:
                print("SKIP: openai (no key)")
            if CLAUDE_KEY:
                await run_one("anthropic", "Hello from test")
            else:
                print("SKIP: anthropic (no key)")
            if GEMINI_KEY:
                await run_one("google", "Hello from test")
            else:
                print("SKIP: google (no key)")
    finally:
        cleanup()

if __name__ == "__main__":
    asyncio.run(main())
