import discord
from discord import app_commands, Interaction, Thread
from common.session.user_session_manager import user_session_manager
from common.session.server_session_manager import server_session_manager
from common.session.prompt_loader import read_snippet_for_ctx
from common.utils.thread_utils import is_thread_managed
from ui.discord.discord_thread_context import context_manager
from ai.openai.openai_api import call_chatgpt

HELP_TEXT = {
    "usage": "/ac_summary",
    "description": "現在のトピックを要約して、その内容で新しくトピックを始めます。以前の会話内容は忘れます。"
}

SERVICE_NAME = "discord"

@app_commands.command(name="ac_summary", description=HELP_TEXT["description"])
async def ac_summarycommand(interaction: Interaction):
    await interaction.response.defer(thinking=True, ephemeral=True)
    if not isinstance(interaction.channel, Thread):
        await interaction.followup.send("❌ スレッド外では実行できません。", ephemeral=True)
        return

    thread = interaction.channel
    if not is_thread_managed(SERVICE_NAME, str(interaction.guild_id), thread.id):
        await interaction.followup.send("❌ AIChatBotはこのスレッドに参加していません。", ephemeral=True)
        return

    # 認証情報チェック
    user_id = interaction.user.id
    guild_id = interaction.guild.id
    if not user_session_manager.has_session(user_id):
        if not server_session_manager.has_session(guild_id):
            await interaction.followup.send("⚠️ 認証情報を /ac_auth で登録してください。")
            return

    # 認証情報を取得（User優先）
    if user_session_manager.has_session(user_id):
        auth_data = user_session_manager.get_session(user_id)
    else:
        auth_data = server_session_manager.get_session(guild_id)

    if not context_manager.is_initialized(thread.id):
        await context_manager.ensure_initialized(thread)

    # 履歴取得
    hist = list(context_manager.get_context(thread.id))
    if not hist:
        await interaction.followup.send("❌ 要約する内容がありません。", ephemeral=True)
        return

    # サマリー用システムプロンプト（summary.txt を使用）
    summary_sys = read_snippet_for_ctx("summary", user_id, guild_id)
    if not summary_sys.strip():
        await interaction.followup.send("⚠️ 要約用のプロンプトが見つかりませんでした。", ephemeral=True)
        return

    # Discord と同じメッセージ形式（先頭に system を置く）
    message_list: list[str] = []
    message_list.append("\\s" + summary_sys)
    for mm in hist:
        message_list.append(mm["message"])

    # LLM 呼び出し
    reply = ""

    # OpenAIの場合
    if auth_data["chat"]["provider"] == "OpenAI":
        reply = await call_chatgpt(
            message_list,
            auth_data["chat"]["api_key"],
            auth_data["chat"]["model"],
            auth_data["chat"].get("max_tokens", 2048),
        )

    await thread.send(
        f"💬/ac_summary: 要約した内容で新しくトピックを始めます。\n"
        f"・取り消す場合は、このメッセージを削除してください。\n"
        f"{reply}"
    )
    context_manager.reset_context(thread.id)
    await interaction.followup.send("✅ ここまでの内容を要約しました。")

def register(tree: app_commands.CommandTree, client: discord.Client, guild: discord.Object = None):
    if guild:
        tree.add_command(ac_summarycommand, guild=guild)
    else:
        tree.add_command(ac_summarycommand)
