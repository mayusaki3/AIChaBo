# -*- coding: utf-8 -*-
"""
T04_ChatCore_01_chat_core_test.py
目的: Discord 非依存の chat_core をモック LLM で検証
実行例: python -m utiltests.T04_ChatCore_01_chat_core_test
"""
import asyncio
import types, sys
from ui.discord.services.chat_core import run_chat_core
from utiltests._report import make_reporter

async def _fake_llm(context_list, api_key, model, **_):
    """最終のユーザー発話っぽい要素を拾ってエコー"""
    last_user = ""
    for m in reversed(context_list):
        if isinstance(m, str) and not m.startswith("\\s"):
            last_user = m
            break
    return f"[mock:{model}] {last_user[:100]}"

def _inject_fake(module_name, func_name):
    """対象モジュールのチャット呼び出し関数を偽装実装で差し替え"""
    m = types.ModuleType(module_name)
    async def _fn(*a, **kw): return await _fake_llm(*a, **kw)
    setattr(m, func_name, _fn)
    sys.modules[module_name] = m

def main():
    rep = make_reporter("T04-01")
    rep.banner("ChatCore with fake LLM")
    # 主要3プロバイダの呼び先を差し替え（OpenAI/Gemini/Claude）
    _inject_fake("ai.openai.openai_api", "call_chatgpt")
    _inject_fake("ai.gemini.gemini_api", "call_gemini_chat")
    _inject_fake("ai.claude.claude_api", "call_claude_chat")

    async def _run(provider):
        auth = {"chat": {"provider": provider, "api_key": "DUMMY", "model": "test-model"}}
        ctx  = ["\\s system prompt", "user: こんにちは", "assistant: こちらこそ", "user: 今日は？"]
        out = await run_chat_core(ctx, auth)
        assert out.startswith("[mock:test-model]"), out

    for prov in ("OpenAI", "Gemini", "Claude"):
        with rep.case(f"{prov} echo"):
            asyncio.run(_run(prov))
    rep.summary()

if __name__ == "__main__":
    main()
