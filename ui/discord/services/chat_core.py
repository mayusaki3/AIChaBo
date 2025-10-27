# ui/discord/services/chat_core.py
# Discord非依存の最小コア。context_list→reply を返す。
from typing import Sequence, Mapping

async def run_chat_core(
    context_list: Sequence[str],
    auth_data: Mapping[str, dict],
) -> str:
    """最小版：プロバイダ分岐だけ持つ。実体は後で拡張。"""
    provider = (auth_data.get("chat", {}) or {}).get("provider")
    api_key  = (auth_data.get("chat", {}) or {}).get("api_key")
    model    = (auth_data.get("chat", {}) or {}).get("model")

    if not provider or not api_key or not model:
        raise RuntimeError("auth_data.chat が不足しています")

    # 本番は openai/gemini/claude の実体を呼ぶ。テストではモック差替え。
    if provider == "OpenAI":
        from ai.openai.openai_api import call_chatgpt as _call
    elif provider == "Gemini":
        from ai.gemini.gemini_api import call_gemini_chat as _call
    elif provider == "Claude":
        from ai.claude.claude_api import call_claude_chat as _call
    else:
        raise RuntimeError(f"unsupported provider: {provider}")

    return await _call(context_list, api_key, model, (auth_data.get("chat") or {}).get("max_tokens", 2048))
