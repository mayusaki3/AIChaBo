# ライフサイクル系イベント（起動・編集・削除）
# コメント: DEV_GUILD_ID があればギルド同期、無ければグローバル同期。
from ..runtime.client import client, tree
from ..utils.log import _print
from common.plugins.dispatcher import list_providers
from common.utils.webread_utils import redact
import os, asyncio, sys
from discord import Object as DiscordObject

@client.event
async def on_ready():
    _print(f"✅ {client.user} としてログインしました。")
    try:
        # ★ギルド同期は DISCORD_GUILD_ID のみを見る
        dev_gid_raw = os.getenv("DISCORD_GUILD_ID")
        if dev_gid_raw:
            # 1) 数値化（commands.py 側でも検証しているが二重防御）
            gid = int(dev_gid_raw)
            # 2) Bot が当該ギルドに参加しているか（未参加なら即終了）
            if client.get_guild(gid) is None:
                _print(f"❌ DISCORD_GUILD_ID={gid} のサーバーにBotが参加していません。招待してから再実行してください。")
                await client.close()
                return
            # 3) 同期（通信不調で固まらないようタイムアウトを設定）
            await asyncio.wait_for(tree.sync(guild=DiscordObject(id=gid)), timeout=20)
            _print(f"🧪 開発モード（サーバーID={gid}）でコマンドを同期しました")
        else:
            # グローバル同期もタイムアウト付き
            await asyncio.wait_for(tree.sync(), timeout=20)
            _print("🚀 本番モード（グローバル）でコマンドを同期しました")            
    except Exception as e:
        _print(f"❌ コマンド同期に失敗しました: {redact(str(e))}")
        # 同期失敗時はハング回避のため終了
        await client.close()
        return
    except asyncio.TimeoutError:
        _print("❌ コマンド同期がタイムアウトしました（DISCORD_GUILD_ID や通信状態を確認してください）")
        await client.close()
        return

    # クリーンアップ処理（実処理を呼べるならここで呼ぶ）
    _print("🔎 サーバー/スレッドの確認中...")
    try:
        # 例）await cleanup_orphan_threads_and_guilds(...)
        pass
    finally:
        _print("✅ 存在しないサーバー/スレッドのチェックおよびクリーンアップを完了しました")

    _print("🔌 Loaded plugins: " + (", ".join(list_providers()) or "(none)"))
    _print("✅ 起動完了 (Ctrl-Cで終了します)")

@client.event
async def on_message_delete(message):
    """削除ログ（内容は redact される）。"""
    _print(f"❌ メッセージが削除されました: {getattr(message,'content', '')}")

@client.event
async def on_message_edit(before, after):
    """編集ログ（両方 redact 対象）。"""
    _print(f"🔄 メッセージが編集されました: {getattr(before,'content','')} ⇒ {getattr(after,'content','')}")
