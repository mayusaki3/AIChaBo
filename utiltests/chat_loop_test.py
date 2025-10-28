# utiltests/chat_loop_test.py
# -*- coding: utf-8 -*-
"""
chat_loop.run() を単体で叩く最小テスト。
- 実装がスタブの状態でも通る（スタブの戻り値が出力されればOK）。
- 実装済みの場合は、non_secret_auth など context 仕様に合わせて入力を調整。
"""

import asyncio
from common.chat.chat_loop import run as chat_run  # 実行対象（スタブでも可）

async def main():
    # chat_loop.run() に渡す context の最小形（プロジェクトの仕様に合わせて拡張可能）
    ctx = {
        "guild_id": 222,
        "thread_id": 333,
        "user_id": 111,
        "options": {},  # サーバー運用オプション（printmsg/threads_only 等）を載せる場所
        "non_secret_auth": {
            # 非機密の“方針”のみ（API キーの解決は chat_loop 側で行う設計）
            "chat": {"provider": "openai", "model": "gpt-4o-mini"}
        },
        # attachments や追加メタが必要ならここに追加
    }

    out = await chat_run("chat_loop の最小テスト入力", ctx)
    print(out)

if __name__ == "__main__":
    # asyncio 実行
    asyncio.run(main())
