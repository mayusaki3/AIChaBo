# 終了処理（Ctrl+C / SIGBREAK / SIGTERM / atexit などから呼ばれる）
# - 二重実行を検知してスキップ表示
# - BACKGROUND_TASKS を cancel→gather
import asyncio, discord
from .client import client, BACKGROUND_TASKS
from ..utils.log import _print

_SHUTDOWN_DONE = False

async def on_graceful_shutdown(reason: str = "unknown"):
    """安全に落とす。二重呼び出しはスキップ。"""
    global _SHUTDOWN_DONE
    if _SHUTDOWN_DONE or getattr(client, "is_closed", lambda: False)():
        _print(f"ℹ️ シャットダウンが要求されました： {reason} - 処理済みのためスキップしました")
        return

    _print(f"ℹ️ シャットダウンが要求されました： {reason}")
    # 1) Presence を隠す（任意）
    try:
        await client.change_presence(status=discord.Status.invisible)
    except Exception:
        pass

    # 2) 背景タスクを停止
    for t in list(BACKGROUND_TASKS):
        try:
            t.cancel()
        except Exception:
            pass
    await asyncio.gather(*BACKGROUND_TASKS, return_exceptions=True)
    BACKGROUND_TASKS.clear()

    # 3) Discordクライアントを閉じる
    try:
        await client.close()
    except Exception:
        pass

    _print("ℹ️ Discordクライアントを閉じました")
    _SHUTDOWN_DONE = True
