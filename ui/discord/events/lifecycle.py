# ライフサイクル系イベント（起動・編集・削除）
# コメント: DEV_GUILD_ID があればギルド同期、無ければグローバル同期。
from ..runtime.client import client, tree
from ..utils.log import _print
from common.plugins.dispatcher import list_providers
from common.utils.redact import redact
from common.secret.store import store
import os, asyncio, sys
from discord import Object as DiscordObject

@client.event
async def on_ready():
    # プラグイン読み込み処理
    _print("🔌 Loaded plugins: " + (", ".join(list_providers()) or "(none)"))

    _print(f"✅ {client.user} としてログインしました。")

    # 機密ストアバックエンド確認
    try:
        _print(f"🔐 機密ストアバックエンド: {store.backend_name()}")
    except Exception:
        _print("🔐 機密ストアバックエンド: (unknown)")

    try:
        # ギルド同期は DISCORD_GUILD_ID のみを見る
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

    # クリーンアップ処理
    _print("🔎 サーバー/スレッドの確認中...")
    try:
        # --- 参加していないサーバーの検出とクリーンアップ（サーバーID単位） ---
        from common.utils import thread_utils
        existing_server_ids = {str(guild.id) for guild in client.guilds}
        thread_utils.clean_deleted_servers("discord", existing_server_ids)

        # --- すべてのサーバーで、実在スレッド一覧を走査して存在しない記録を削除 ---
        import discord as _discord
        for guild in client.guilds:
            server_id = str(guild.id)
            thread_ids = set()
            # 各テキストチャンネルからスレッドを収集（アクティブ＋公開/非公開アーカイブ）
            for channel in guild.text_channels:
                # アクティブ
                for t in channel.threads:
                    thread_ids.add(str(t.id))
                # 公開アーカイブ
                try:
                    async for t in channel.archived_threads(limit=None):
                        thread_ids.add(str(t.id))
                except (_discord.Forbidden, _discord.HTTPException):
                    pass
                # 非公開アーカイブ（Botが参加している場合は joined=True で取得可能）
                for joined in (True, False):
                    try:
                        async for t in channel.archived_threads(private=True, joined=joined, limit=None):
                            thread_ids.add(str(t.id))
                    except (_discord.Forbidden, _discord.HTTPException, AttributeError):
                        pass
            # thread_utils に記録されている管理対象のうち、実在しないものを削除
            thread_utils.clean_deleted_threads("discord", server_id, thread_ids)
    finally:
        _print("✅ 存在しないサーバー/スレッドのチェックおよびクリーンアップを完了しました")

    _print("✅ 起動完了 (Ctrl-Cで終了します)")

@client.event
async def on_message_delete(message):
    """削除ログ（内容は redact される）。"""
    _print(f"❌ メッセージが削除されました: {getattr(message,'content', '')}")

@client.event
async def on_message_edit(before, after):
    """編集ログ（両方 redact 対象）。"""
    _print(f"🔄 メッセージが編集されました: {getattr(before,'content','')} ⇒ {getattr(after,'content','')}")
