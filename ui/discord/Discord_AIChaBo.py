import sys
import os

# プロジェクトルートをモジュール探索パスに追加
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from dotenv import load_dotenv
import logging, os, asyncio, signal, atexit, sys
from ui.discord.discord_handler import client, on_graceful_shutdown

async def _main():
    load_dotenv()
    for noisy in ("httpx", "openai", "anthropic", "google", "aiohttp"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    token = os.getenv("DISCORD_BOT_TOKEN", "")
    if not token:
        print("❌ DISCORD_BOT_TOKEN が未設定です（.env か環境変数を確認してください）")
        return

    # Ctrl+C / タスク終了要求 → シャットダウンへ
    shutdown_event = asyncio.Event()
    def _signal_handler(*_):
        shutdown_event.set()
    # Windows: SIGINT(Ctrl+C) / SIGBREAK(Ctrl+Break) は捕捉可能
    signal.signal(signal.SIGINT, _signal_handler)
    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, _signal_handler)
    # 一部環境で使える場合のみ
    if hasattr(signal, "SIGTERM"):
        try:
            signal.signal(signal.SIGTERM, _signal_handler)
        except Exception:
            pass

    # プロセス終了時の保険
    atexit.register(lambda: asyncio.run(on_graceful_shutdown(reason="atexit")))

    # Bot起動
    bot_task = asyncio.create_task(client.start(token))
    # 終了シグナル待ち
    await shutdown_event.wait()
    # シャットダウン処理
    await on_graceful_shutdown(reason="signal")
    # client.start の終了を待つ
    try:
        await bot_task
    except asyncio.CancelledError:
        pass

if __name__ == "__main__":
    try:
        asyncio.run(_main())
    except KeyboardInterrupt:
        # 念のため
        try:
            asyncio.run(on_graceful_shutdown(reason="KeyboardInterrupt"))
        except Exception:
            pass
        sys.exit(0)
