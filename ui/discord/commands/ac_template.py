# ui/discord/commands/ac_template.py
# ------------------------------------------------------------
# /ac_template: 認証情報設定用テンプレート（JSONC）をダウンロード
# - 以下のファイルを提供する
#   common/template/auth_template.jsonc
# ------------------------------------------------------------
from pathlib import Path
import discord
from discord import app_commands, Interaction

HELP_TEXT = {
    "description": "認証情報設定用テンプレート（JSONC）をダウンロードします。",
    "usage": "/ac_template"
}

def get_command():
    return app_commands.Command(
        name="ac_template",
        description=HELP_TEXT["description"],
        callback=ac_template_command,
    )

async def ac_template_command(interaction: Interaction):
    try:
        file_path = Path(__file__).resolve().parent.parent.parent.parent / "common/template/auth_template.jsonc"
        if not file_path.exists():
            await interaction.response.send_message("テンプレートファイルが見つかりません。", ephemeral=True)
            return

        await interaction.response.send_message(
            content="以下が認証情報設定用テンプレートです。\nダウンロードして記入後、/ac_auth でアップロードしてください。",
            file=discord.File(fp=file_path, filename="auth_template.jsonc"),
            ephemeral=True
        )
    except Exception as e:
        await interaction.response.send_message(f"エラーが発生しました: {e}", ephemeral=True)
