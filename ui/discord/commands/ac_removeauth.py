# ui/discord/commands/ac_removeauth.py
# ------------------------------------------------------------
# /ac_removeauth: 登録したAIチャットの認証情報を削除
# - 認証情報を共有していた場合、共有した認証情報は維持される。
#   （共有解除は /ac_authunsharing で別途実行する必要がある）
# ------------------------------------------------------------
import discord
from discord import app_commands, Interaction
from common.session.user_session_manager import user_session_manager
from common.secret.store import store
from common.session.server_session_manager import server_session_manager

HELP_TEXT = {
    "usage": "/ac_removeauth",
    "description": "登録したAIチャット/画像認識/画像生成の認証情報を削除します。"
}

def get_command():
    return app_commands.Command(
        name="ac_removeauth",  # ★修正
        description=HELP_TEXT["description"],
        callback=ac_removeauth_command,
    )

async def ac_removeauth_command(interaction: Interaction):
    await interaction.response.defer(thinking=True, ephemeral=True)

    auth_data = user_session_manager.get_session(interaction.user.id)
    if not auth_data:
        await interaction.followup.send("❌ 認証情報は登録されていません。", ephemeral=True)
        return

    user_session_manager.clear_session(interaction.user.id)

    # 共有が残っているかを確認（共有“非機密” or サーバー鍵）
    gid = interaction.guild.id if interaction.guild else None
    shared_notice = ""
    if gid:
        shared_cfg = server_session_manager.get_shared_auth_config(gid)
        try:
            has_any_srv_keys = getattr(store, "has_server_any_key", None)
            shared_keys = bool(has_any_srv_keys(gid)) if has_any_srv_keys else bool(store.get_server_keys(gid))
        except Exception:
            shared_keys = False
        if shared_cfg or shared_keys:
            shared_notice = "\nℹ️ 認証情報の共有は維持されます。解除するには /ac_authunsharing を実行してください。"

    await interaction.followup.send("✅ 認証情報を削除しました。" + shared_notice, ephemeral=True)
