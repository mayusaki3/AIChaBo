# common/chat/chat_loop.py
from __future__ import annotations
from typing import Any, Dict

async def run(user_text: str, context: Dict[str, Any]) -> str:
    # TODO: ここに実処理（プロバイダ選択→鍵解決→呼び出し）を実装
    # ひとまず通すための最小戻り値
    return f"（chat_loop未配線）入力: {user_text[:80]}"
