import discord
from discord import app_commands, Interaction, Thread
from common.utils.thread_utils import is_thread_managed
from ui.discord.discord_thread_context import context_manager

HELP_TEXT = {
    "usage": "/ac_newtopic",
    "description": "新しくトピックを始めます。以前の会話内容は忘れます。"
}

SERVICE_NAME = "discord"

@app_commands.command(name="ac_newtopic", description=HELP_TEXT["description"])
async def ac_newtopiccommand(interaction: Interaction):
    await interaction.response.defer(thinking=True, ephemeral=True)
    if not isinstance(interaction.channel, Thread):
        await interaction.followup.send("❌ スレッド外では実行できません。", ephemeral=True)
        return

    thread = interaction.channel
    if not is_thread_managed(SERVICE_NAME, interaction.guild_id, thread.id):
        await interaction.followup.send("⚠️ あいちゃぼはこのスレッドに参加していません。", ephemeral=True)
        return

    # AIチャットスレッドのコンテキスト状態
    context_manager.clear_context(thread.id)
    await thread.send(
        f"💬/ac_newtopic: 新しくトピックを始めます。以前の会話内容は忘れます。\n"
        f"・取り消す場合は、このメッセージを削除してください。"
    )

    await interaction.followup.send("✅ 新しいトピックを始めました。", ephemeral=True)

def register(tree: app_commands.CommandTree, client: discord.Client, guild: discord.Object = None):
    if guild:
        tree.add_command(ac_newtopiccommand, guild=guild)
    else:
        tree.add_command(ac_newtopiccommand)
