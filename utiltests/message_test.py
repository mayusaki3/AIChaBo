# utiltests/message_test.py
# -*- coding: utf-8 -*-
"""
Discord を介さずに、共通層 message.handle_incoming_message() を直接叩く最小テスト。
- run_once_for_test() は common/chat/message.py に用意したテスト用ヘルパ。
- 「スレッド内のみ」運用に引っかからないよう、guild_id と thread_id を与える。
- 返信はコンソールにそのまま print される（Discord の 2000 文字分割はここでは未適用）。
"""

import asyncio
from common.chat.message import run_once_for_test  # 共通層のテスト用関数

if __name__ == "__main__":
    # ユーザーID/サーバーID/スレッドID はダミーでOK
    asyncio.run(
        run_once_for_test(
            user_text="テストです。通常チャットの最小経路を通します。",
            user_id=111,
            guild_id=222,
            thread_id=333,  # ← スレッド内扱いにすることでポリシー違反を回避
        )
    )
