# -*- coding: utf-8 -*-
"""
T06_Message_01_message_test.py
目的: Discord を介さず共通層 message.run_once_for_test() の最小経路を検証
実行例: python -m tests.T06_Message_01_message_test
"""
import asyncio
from tests._report import make_reporter
from common.chat.message import run_once_for_test

async def _one():
    """スレッド限定運用に引っかからないよう、guild/thread を付与して実行"""
    return await run_once_for_test(
        user_text="テストです。通常チャット最小経路を通します。",
        user_id=111,
        guild_id=222,
        thread_id=333,
    )

def main():
    rep = make_reporter("T06-01")
    rep.banner("Message minimal path")
    with rep.case("run_once_for_test"):
        out = asyncio.run(_one())
        # 返却値は None（送信済み）または文字列（実装次第）を許容
        assert out is None or isinstance(out, str)
    rep.summary()

if __name__ == "__main__":
    main()
