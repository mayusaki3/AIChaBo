# ui/discord/commands/ac_authunsharing.py
import json
import discord
from discord import app_commands, Interaction
from common.session.server_session_manager import server_session_manager

HELP_TEXT = {
    "usage": "/ac_authunsharing",
    "description": "認証情報の共有を解除します。"
}

def get_command():
    return None

@app_commands.command(name="ac_authunsharing", description=HELP_TEXT["description"])
async def ac_authunsharing_command(interaction: Interaction):
    await interaction.response.defer(thinking=True, ephemeral=True)

    guild_id = interaction.guild_id
    auth_data = server_session_manager.get_session(guild_id)
    if not auth_data:
        await interaction.followup.send("❌ 認証情報は共有されていません。", ephemeral=True)
        return
    server_session_manager.clear_session(guild_id)
    await interaction.followup.send("✅ 認証情報の共有を解除しました", ephemeral=True)
