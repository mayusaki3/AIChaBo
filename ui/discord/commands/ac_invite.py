import discord
from discord import app_commands, Interaction, Thread
from common.utils.thread_utils import add_thread_to_server, is_thread_managed

HELP_TEXT = {
    "usage": "/ac_invite",
    "description": "🧵スレッド内のみ: あいちゃぼを現在のスレッドに招待します。"
}

SERVICE_NAME = "discord"

@app_commands.command(name="ac_invite", description=HELP_TEXT["description"])
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
        if thread.owner_id != interaction.client.user.id:
            # Botがスレッド作成者でない場合
            if thread.is_private() and interaction.user.id != thread.owner_id:
                await interaction.followup.send("⚠️ プライベートスレッドであいちゃぼを招待するには、スレッド作成者である必要があります。", ephemeral=True)
                return

            # Botが招待できるか試行
            try:
                await thread.add_user(interaction.client.user)
            except discord.Forbidden:
                await interaction.followup.send("⚠️ あいちゃぼを招待する権限がありません。\n@あいちゃぼ に memtion してから再実行してください。", ephemeral=True)
                return

        add_thread_to_server(SERVICE_NAME, interaction.guild_id, thread.id)
        await interaction.followup.send("✅ あいちゃぼをこのスレッドに招待しました。", ephemeral=True)
        await thread.send(
            f"💬/ac_invite: あいちゃぼが参加しました。\n"
            f"・このスレッド内でのメッセージは、投稿者が登録した認証情報に基づいて外部の AI に送信・応答されます。"
        )

    except Exception as e:
        await interaction.followup.send(f"❌ あいちゃぼの招待に失敗しました: {e}", ephemeral=True)

def register(tree: app_commands.CommandTree, client: discord.Client, guild: discord.Object = None):
    if guild:
        tree.add_command(ac_invite_command, guild=guild)
    else:
        tree.add_command(ac_invite_command)
