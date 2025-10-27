# 起動スクリプト（asyncio.run + signal/atexit で安全に終了）
import os, asyncio, signal, atexit, logging, pathlib
from dotenv import load_dotenv
from ui.discord.runtime.client import client, tree
from ui.discord.runtime.shutdown import on_graceful_shutdown
# イベントをimportすると @client.event が実行される
from ui.discord.events import lifecycle, message  # noqa
from ui.discord.services.commands import register_all

async def _main():
    load_dotenv()
    # SDK系のverboseログを抑制（秘匿情報が混入しないよう最低限の防御）
    for noisy in ("httpx","openai","anthropic","google","aiohttp"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    root = pathlib.Path(__file__).resolve().parents[2]
    version = "v0.01"
    try:
        vfile = root / "VERSION"
        if vfile.exists():
            version = vfile.read_text(encoding="utf-8").strip() or version
    except Exception:
        pass
    banner = f"😊 AIChaBo/あいちゃぼ {version}"
    print("+-------------------------------------------------")
    print(f"| {banner} 起動します。")
    print("+-------------------------------------------------")

    register_all(tree)

    token = os.getenv("DISCORD_BOT_TOKEN", "")
    if not token:
        print("❌ DISCORD_BOT_TOKEN が未設定です（.env か環境変数を確認してください）")
        return

    # 終了シグナル（Ctrl+C等）待ちの仕組み
    shutdown_event = asyncio.Event()
    def _sig(*_): shutdown_event.set()
    signal.signal(signal.SIGINT, _sig)
    if hasattr(signal,"SIGBREAK"): signal.signal(signal.SIGBREAK, _sig)
    if hasattr(signal,"SIGTERM"):
        try: signal.signal(signal.SIGTERM, _sig)
        except Exception: pass

    # atexitの保険（signalで閉じた後は二重実行をスキップする実装）
    atexit.register(lambda: asyncio.run(on_graceful_shutdown("atexit")))

    # 起動
    bot_task = asyncio.create_task(client.start(token))
    # Bot終了 or Ctrl+C の“どちらか早い方”で先に進む
    done, pending = await asyncio.wait(
        {bot_task, asyncio.create_task(shutdown_event.wait())},
        return_when=asyncio.FIRST_COMPLETED,
    )
    # Ctrl+C 以外（＝on_ready側でclient.close済み）のケースでは、ここで静かに終了
    if bot_task in done:
        try:
            await bot_task  # エラーあればここで受ける（今回は静かに落とす）
        except asyncio.CancelledError:
            pass
        return
    # Ctrl+C の場合は優雅に終了
    await on_graceful_shutdown("signal")
    try:
        await bot_task
    except asyncio.CancelledError:
        pass

if __name__ == "__main__":
    asyncio.run(_main())
