# ui/discord/commands/ac_authunsharing.py
# ------------------------------------------------------------
# /ac_authunsharing: 共有停止
# - SecretStore のサーバー鍵を削除
# - ServerSession の共有“非機密”設定を削除
# ------------------------------------------------------------
import json
import discord
from discord import app_commands, Interaction
from common.secret.store import store
from common.session.server_session_manager import server_session_manager

HELP_TEXT = {
    "usage": "/ac_authunsharing",
    "description": "認証情報の共有を解除します。"
}

def get_command():
    return app_commands.Command(
        name="ac_authunsharing",
        description=HELP_TEXT["description"],
        callback=ac_authunsharing_command,
    )

async def ac_authunsharing_command(interaction: Interaction):
    await interaction.response.defer(thinking=True, ephemeral=True)

    guild_id = interaction.guild_id
    # 共有有無チェック（共有“非機密” or サーバー鍵）
    shared_cfg = server_session_manager.get_shared_auth_config(guild_id)
    try:
        has_any_srv_keys = getattr(store, "has_server_any_key", None)
        shared_keys = bool(has_any_srv_keys(guild_id)) if has_any_srv_keys else bool(store.get_server_keys(guild_id))
    except Exception:
        shared_keys = False
    if not shared_cfg and not shared_keys:
        await interaction.followup.send("❌ 認証情報は共有されていません。", ephemeral=True)
        return
    # 共有停止＝サーバー鍵＋共有“非機密”の両方を削除
    store.delete_server_keys(guild_id)
    server_session_manager.clear_shared_auth_config(guild_id)
    await interaction.followup.send("✅ 認証情報の共有を解除しました。", ephemeral=True)
