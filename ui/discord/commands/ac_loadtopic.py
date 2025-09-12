import discord
from discord import app_commands, Interaction, Thread
from common.utils.thread_utils import is_thread_managed
from ui.discord.discord_thread_context import context_manager

HELP_TEXT = {
    "usage": "/ac_loadtopic",
    "description": "現在のトピックを読み直します。過去メッセージを編集/削除した場合に使用します。"
}

SERVICE_NAME = "discord"

@app_commands.command(name="ac_loadtopic", description=HELP_TEXT["description"])
async def ac_loadtopiccommand(interaction: Interaction):
    await interaction.response.defer(thinking=True, ephemeral=True)
    if not isinstance(interaction.channel, Thread):
        await interaction.followup.send("❌ スレッド外では実行できません。", ephemeral=True)
        return

    thread = interaction.channel
    if not is_thread_managed(SERVICE_NAME, interaction.guild_id, thread.id):
        await interaction.followup.send("⚠️ あいちゃぼはこのスレッドに参加していません。", ephemeral=True)
        return

    # AIチャットスレッドのコンテキスト状態
    await context_manager.load_context_from_history(thread)
    context = context_manager.get_context(thread.id)
    await interaction.followup.send(f"✅ トピックを {len(context)} 件読み込みました。", ephemeral=True)

def register(tree: app_commands.CommandTree, client: discord.Client, guild: discord.Object = None):
    if guild:
        tree.add_command(ac_loadtopiccommand, guild=guild)
    else:
        tree.add_command(ac_loadtopiccommand)
