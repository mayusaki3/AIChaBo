# utiltests/chat_core_test.py
# Discordなしで run_chat_core を検証（LLM呼び出しをモック）
import asyncio
from ui.discord.services.chat_core import run_chat_core

# ---- モックを差し込むための薄いラッパ（import順に依存しない簡易法） ----
import types, sys

async def _fake_llm(context_list, api_key, model, max_tokens):
    # 最終ユーザ発話っぽいものを拾ってエコー（十分）
    last_user = ""
    for m in reversed(context_list):
        if isinstance(m, str) and not m.startswith("\\s"):
            last_user = m
            break
    return f"[mock:{model}] {last_user[:100]}"

def _inject_fake(module_name, func_name):
    m = types.ModuleType(module_name)
    async def _fn(*a, **kw): return await _fake_llm(*a, **kw)
    setattr(m, func_name, _fn)
    sys.modules[module_name] = m

def main():
    # OpenAI/Gemini/Claude いずれでも動くよう、必要な箇所にモック注入
    _inject_fake("ai.openai.openai_api", "call_chatgpt")
    _inject_fake("ai.gemini.gemini_api", "call_gemini_chat")
    _inject_fake("ai.claude.claude_api", "call_claude_chat")

    async def _run(provider):
        auth = {"chat": {"provider": provider, "api_key": "DUMMY", "model": "test-model"}}
        ctx  = ["\\s system prompt", "user: こんにちは", "assistant: こちらこそ", "user: 今日は？"]
        out = await run_chat_core(ctx, auth)
        print(provider, "=>", out)
        assert out.startswith("[mock:test-model]"), out

    asyncio.run(_run("OpenAI"))
    asyncio.run(_run("Gemini"))
    asyncio.run(_run("Claude"))
    print("OK")

if __name__ == "__main__":
    main()
