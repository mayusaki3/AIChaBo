# ui/discord/commands/ac_leave.py
# ------------------------------------------------------------
# /ac_leave: あいちゃぼを現在のスレッドから退出
# ------------------------------------------------------------
import discord
from discord import app_commands, Interaction, Thread
from common.utils.thread_utils import remove_thread_from_server, is_thread_managed

HELP_TEXT = {
    "usage": "/ac_leave",
    "description": "🧵スレッド内のみ: あいちゃぼを現在のスレッドから退出させます。"
}

SERVICE_NAME = "discord"

def get_command():
    return app_commands.Command(
        name="ac_leave",
        description=HELP_TEXT["description"],
        callback=ac_leave_command,
    )

async def ac_leave_command(interaction: Interaction):
    await interaction.response.defer(thinking=True, ephemeral=True)
    if not isinstance(interaction.channel, Thread):
        await interaction.followup.send("❌ スレッド外では実行できません。", ephemeral=True)
        return

    thread = interaction.channel
    if not is_thread_managed(SERVICE_NAME, interaction.guild_id, thread.id):
        await interaction.followup.send("⚠️ あいちゃぼはこのスレッドに参加していません。", ephemeral=True)
        return

    try:
        sent_msg = await thread.send(
            f"💬/ac_leave: AIChatBotが退出しました。\n"
            f"・以後のスレッド内でのメッセージは、次の条件を除き外部の AI に送信されることはありません。\n"
            f"・スレッド内のメッセージは、/ac_loadtopic, /ac_summary の処理対象になる場合があります。"
        )
        if thread.owner_id != interaction.client.user.id:
            try:
                await thread.remove_user(interaction.client.user)
            except discord.Forbidden:
                if sent_msg:
                    await sent_msg.delete()
                await interaction.followup.send("⚠️ あいちゃぼを退出させる権限がありません。", ephemeral=True)
                return

        remove_thread_from_server(SERVICE_NAME, interaction.guild_id, thread.id)
        await interaction.followup.send("👋 あいちゃぼはスレッドから退出しました。", ephemeral=True)

    except Exception as e:
        await interaction.followup.send(f"❌ あいちゃぼの退出に失敗しました: {e}", ephemeral=True)
