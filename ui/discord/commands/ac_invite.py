# ui/discord/commands/ac_invite.py
# ------------------------------------------------------------
# /ac_invite: あいちゃぼを現在のスレッドに招待
# ------------------------------------------------------------
import discord
from discord import app_commands, Interaction, Thread
from common.utils.thread_utils import add_thread_to_server, is_thread_managed

HELP_TEXT = {
    "usage": "/ac_invite",
    "description": "🧵スレッド内のみ: あいちゃぼを現在のスレッドに招待します。"
}

SERVICE_NAME = "discord"

def get_command():
    return app_commands.Command(
        name="ac_invite",
        description=HELP_TEXT["description"],
        callback=ac_invite_command,
    )

async def ac_invite_command(interaction: Interaction):
    await interaction.response.defer(thinking=True, ephemeral=True)
    if not isinstance(interaction.channel, Thread):
        await interaction.followup.send("❌ スレッド外では実行できません。", ephemeral=True)
        return

    thread = interaction.channel
    if is_thread_managed(SERVICE_NAME, interaction.guild_id, thread.id):
        await interaction.followup.send("⚠️ あいちゃぼは既にこのスレッドに参加しています。", ephemeral=True)
        return

    try:
        # public/private を堅牢に判定
        is_private = (
            (hasattr(thread, "is_private") and callable(getattr(thread, "is_private")) and thread.is_private()) or
            (getattr(thread, "type", None) == discord.ChannelType.private_thread)
        )

        if not is_private:
            # Public thread: Bot は join で参加
            await thread.join()
        else:
            # Private thread: オーナーのみ Bot を招待可能
            if interaction.user.id != thread.owner_id:
                await interaction.followup.send(
                    "⚠️ プライベートスレッドであいちゃぼを招待するには、スレッド作成者である必要があります。",
                    ephemeral=True
                )
                return
            # Bot を private に招待（Member を優先）
            bot_member = interaction.guild.me if interaction.guild else None
            try:
                await thread.add_user(bot_member or interaction.client.user)
            except discord.Forbidden:
                await interaction.followup.send(
                    "⚠️ あいちゃぼを招待する権限がありません。\n@あいちゃぼ に mention してから再実行してください。",
                    ephemeral=True
                )
                return
 
        add_thread_to_server(SERVICE_NAME, interaction.guild_id, thread.id)
        await interaction.followup.send("✅ あいちゃぼをこのスレッドに招待しました。", ephemeral=True)
        await thread.send(
            f"💬/ac_invite: あいちゃぼが参加しました。\n"
            f"・このスレッド内でのメッセージは、投稿者が登録した認証情報に基づいて外部の AI に送信・応答されます。"
        )

    except Exception as e:
        await interaction.followup.send(f"❌ あいちゃぼの招待に失敗しました: {e}", ephemeral=True)
