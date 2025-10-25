# ui/discord/commands/ac_help.py
# ------------------------------------------------------------
# /ac_help: すべての /ac_ コマンドのヘルプを表示
# - 表示内容は、各コマンドの HELP_TEXT より自動収集
# ------------------------------------------------------------
import discord
from discord import app_commands
from ui.discord.services.commands import list_registered_commands

HELP_TEXT = {
    "usage": "/ac_help",
    "description": "すべての /ac_ コマンドのヘルプを表示します。"
}

def get_command():
    return app_commands.Command(
        name="ac_help",
        description=HELP_TEXT["description"],
        callback=ac_help_command,
    )
async def ac_help_command(interaction: discord.Interaction):
    """ローダが保持する登録レジストリからヘルプを組み立てる。"""
    rows = []
    for meta in list_registered_commands():
        usage = meta.get("usage") or f"/{meta.get('name','')}"
        desc  = meta.get("description") or "(未定義)"
        rows.append(f"**{usage}**\n説明: {desc}")

    embed = discord.Embed(
        title="あいちゃぼ コマンドヘルプ",
        description="\n\n".join(rows) if rows else "（登録済みの /ac_ コマンドがありません）",
        color=0x00ffcc
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)
