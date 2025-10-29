# utiltests/mocks/mock_chat.py
from typing import List

async def mock_chat(provider: str, context_list: List[str]) -> str:
    if context_list and context_list[0].strip().lower() == "mock":
        instr = context_list[1].strip() if len(context_list) > 1 else ""
        return f"[MOCK/{provider}] {instr}"
    preview = " / ".join(context_list[-2:]) if context_list else ""
    return f"[MOCK/{provider}] echo: {preview}"
