import json
import discord
from discord import app_commands, Interaction
from common.utils import jsonc

from common.session.user_session_manager import user_session_manager
# プロンプトの読み込みを /ac_auth 成功時に実行
from common.session.prompt_loader import load_for_ctx, AuthNotConfigured

# 既存の OpenAI 検証ユーティリティ（現状は OpenAI のみ対応）
from ai.openai.validator import (
    is_valid_openai_key,
    is_openai_chat_model_available,
    is_openai_vision_model_available,
    is_openai_imagegen_model_available,
)

HELP_TEXT = {
    "usage": "/ac_auth <file>",
    "description": "あいちゃぼが使用するAIチャットの認証情報を登録します。"
}

def _normalize_provider(name: str) -> str:
    n = (name or "").strip().lower()
    if n in ("openai", "oai", "gpt"):
        return "openai"
    if n in ("google", "gemini", "g"):
        return "google"
    if n in ("anthropic", "claude", "a"):
        return "claude"
    if n in ("default",):
        return "default"
    return n or "default"

def _require_fields(section: dict, fields: list[str], prefix: str) -> list[str]:
    missing = []
    for f in fields:
        if f not in section or section.get(f) in (None, ""):
            missing.append(f"{prefix}.{f}")
    return missing

# --------------------------
# /ac_auth 本体
# --------------------------
@app_commands.command(name="ac_auth", description=HELP_TEXT["description"])
async def ac_auth_command(interaction: Interaction, file: discord.Attachment):
    if not interaction.response.is_done():
        try:
            await interaction.response.defer(ephemeral=True)
        except discord.errors.NotFound:
            return
    try:
        # 拡張子チェック（.json / .jsonc）
        if not (file.filename.endswith(".json") or file.filename.endswith(".jsonc")):
            await interaction.followup.send("❌ .json または .jsonc ファイルを添付してください。", ephemeral=True)
            return

        # 読み込み（UTF-8/BOM対応）
        raw = await file.read()
        text = raw.decode("utf-8-sig", errors="ignore")

        # JSONC → JSON
        try:
            auth_json = jsonc.loads_jsonc(text)
        except Exception as e:
            await interaction.followup.send(f"❌ JSONC/JSON の読み込みに失敗しました: {e}", ephemeral=True)
            return

        # ---------------- 構造検証（最低限） ----------------
        missing = []
        if "template_version" not in auth_json:
            missing.append("template_version")
        else:
            if str(auth_json["template_version"]).strip() != "1.0":
                await interaction.followup.send("❌ 認証テンプレートの `template_version` は '1.0' を指定してください。", ephemeral=True)
                return

        for key in ("chat", "vision", "imagegen"):
            if key not in auth_json or not isinstance(auth_json[key], dict):
                missing.append(key)
        if missing:
            await interaction.followup.send(f"❌ 必須セクションが不足しています: {', '.join(missing)}", ephemeral=True)
            return

        # セクション必須フィールド
        missing = []
        missing += _require_fields(auth_json["chat"],    ["provider", "api_key", "model"], "chat")
        missing += _require_fields(auth_json["vision"],  ["provider", "api_key", "model"], "vision")
        missing += _require_fields(auth_json["imagegen"],["provider", "api_key", "model"], "imagegen")
        if missing:
            await interaction.followup.send(f"❌ 必須フィールドが不足しています: {', '.join(missing)}", ephemeral=True)
            return

        # provider 正規化
        chat_provider   = _normalize_provider(auth_json["chat"]["provider"])
        vision_provider = _normalize_provider(auth_json["vision"]["provider"])
        image_provider  = _normalize_provider(auth_json["imagegen"]["provider"])

        # ---------------- 実アカウント検証（現状 OpenAI のみ） ----------------
        try:
            # Chat
            if chat_provider != "openai":
                raise ValueError("provider(chat) unsupported")
            chat_key   = auth_json["chat"]["api_key"].strip()
            chat_model = auth_json["chat"]["model"].strip()
            if (await is_valid_openai_key(chat_key)) is not True:
                await interaction.followup.send("❌ Chat 用の API キーは利用できません。", ephemeral=True)
                return
            if not await is_openai_chat_model_available(chat_key, chat_model):
                await interaction.followup.send(f"❌ Chat モデル `{chat_model}` は利用できません。", ephemeral=True)
                return

            # Vision
            if vision_provider != "openai":
                raise ValueError("provider(vision) unsupported")
            vision_key   = auth_json["vision"]["api_key"].strip()
            vision_model = auth_json["vision"]["model"].strip()
            if (await is_valid_openai_key(vision_key)) is not True:
                await interaction.followup.send("❌ Vision 用の API キーは利用できません。", ephemeral=True)
                return
            if not await is_openai_vision_model_available(vision_key, vision_model):
                await interaction.followup.send(f"❌ Vision モデル `{vision_model}` は利用できません。", ephemeral=True)
                return

            # ImageGen
            if image_provider != "openai":
                raise ValueError("provider(imagegen) unsupported")
            image_key    = auth_json["imagegen"]["api_key"].strip()
            image_model  = auth_json["imagegen"]["model"].strip()
            image_size   = str(auth_json["imagegen"].get("size", "")).strip() or "1024x1024"
            image_quality= str(auth_json["imagegen"].get("quality", "")).strip() or "standard"
            if (await is_valid_openai_key(image_key)) is not True:
                await interaction.followup.send("❌ ImageGen 用の API キーは利用できません。", ephemeral=True)
                return
            if not await is_openai_imagegen_model_available(image_key, image_model, image_size, image_quality):
                await interaction.followup.send(f"❌ ImageGen モデル `{image_model}` は利用できません。", ephemeral=True)
                return

        except ValueError:
            await interaction.followup.send("❌ 現在は provider='OpenAI' のみ対応しています。", ephemeral=True)
            return

        # ---------------- セッション保存（ユーザーごと） ----------------
        # そのまま格納（プロバイダ名は元の値でも、取り出し時に正規化します）
        user_session_manager.set_session(interaction.user.id, auth_json)

        # ---------------- プロンプト読み込み（/ac_auth 成功時に実行） ----------------
        try:
            guild_id = interaction.guild.id if interaction.guild else 0
            # 認証は今保存したので、ユーザー優先で load_for_ctx がプロバイダを解決します
            load_for_ctx(user_id=interaction.user.id, guild_id=guild_id, force=True)
            await interaction.followup.send("✅ 認証情報を登録しました。プロンプトを読み込みました。", ephemeral=True)
        except AuthNotConfigured:
            # 通常ここには来ない（いま登録したため）
            await interaction.followup.send("✅ 認証情報を登録しました。（プロンプト読み込みは次回リクエスト時に実施）", ephemeral=True)

    except Exception as e:
        try:
            await interaction.followup.send(f"❌ エラーが発生しました: {e}", ephemeral=True)
        except Exception:
            pass

def register(tree: app_commands.CommandTree, client: discord.Client, guild: discord.Object = None):
    if guild:
        tree.add_command(ac_auth_command, guild=guild)
    else:
        tree.add_command(ac_auth_command)
