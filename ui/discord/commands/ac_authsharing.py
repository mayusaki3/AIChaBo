# ui/discord/commands/ac_authsharing.py
# ------------------------------------------------------------
# /ac_authsharing: 現在のユーザー設定をサーバーへ“共有”
# - 非機密( provider/model/追加パラメータ/プロンプト等 ) → ServerSession に保存
# - APIキー → SecretStore の「サーバー鍵」として保存
# ------------------------------------------------------------
import discord
from discord import app_commands, Interaction
from common.session.user_session_manager import user_session_manager
from common.session.server_session_manager import server_session_manager
from common.secret.store import store
from common.utils.webread_utils import redact

HELP_TEXT = {
    "usage": "/ac_authsharing",
    "description": "認証情報が未登録の人に現在の認証情報をサーバー単位で共有します。"
}

def get_command():
    return app_commands.Command(
        name="ac_authsharing",  # ★修正
        description=HELP_TEXT["description"],
        callback=ac_authsharing_command,
    )

async def ac_authsharing_command(interaction: Interaction):
    await interaction.response.defer(thinking=True, ephemeral=True)

    user_id  = interaction.user.id
    guild_id = interaction.guild_id
    guild    = interaction.guild

    # ユーザー非機密設定（api_keyを含まない想定。念のため後段でstrip）
    user_auth = user_session_manager.get_session(user_id)
    if not user_auth:
        await interaction.followup.send("❌ 共有する認証情報が登録されていません。/ac_auth で登録してください。", ephemeral=True)
        return

    # すでに共有済みかを検出（共有“非機密” or サーバー鍵が存在）
    already_shared_cfg  = bool(server_session_manager.get_shared_auth_config(guild_id))
    try:
        # store.has_server_any_key がある場合は最速で鍵有無を確認
        has_any_srv_keys = getattr(store, "has_server_any_key", None)
        already_shared_key = bool(has_any_srv_keys(guild_id)) if has_any_srv_keys else bool(store.get_server_keys(guild_id))
    except Exception:
        already_shared_key = False
    already_shared = already_shared_cfg or already_shared_key

    # ユーザー名（またはID）を組み立て
    warn_prefix = ""
    if already_shared:
        member = guild.get_member(user_id) if guild else None
        user_name = member.display_name if member else f"id: {user_id}"
        warn_prefix = f"⚠️ {user_name} さんの認証情報が共有されていました。\n"

    # 事前チェック：ユーザーのAPIキーが1件も無ければ何も保存しない（非機密のみ保存を禁止）
    keys_to_copy = {}
    for section in ("chat", "vision", "imagegen"):
        prov = (user_auth.get(section, {}) or {}).get("provider", "").strip().lower()
        if not prov:
            continue
        ukey = store.get_user_key(user_id, prov)
        if ukey:
            keys_to_copy[prov] = ukey
    if not keys_to_copy:
        # 鍵がゼロ → 共有は実施しない（従来メッセージで終了）
        await interaction.followup.send("❌ 共有する認証情報が登録されていません。/ac_auth で登録してください。", ephemeral=True)
        return

    # 保存は“成功か全戻し”の原子性を担保：途中で失敗したらロールバック
    written_providers = []
    try:
        # 1) 共有用“非機密”設定の保存（サーバー単位, api_keyは内部で除去）
        payload = dict(user_auth); payload["shared_by_user_id"] = user_id
        server_session_manager.set_shared_auth_config(guild_id, payload)
        # 2) サーバー鍵の保存（必要プロバイダ分）
        for prov, key_bytes in keys_to_copy.items():
            store.put_server_key(guild_id, prov, key_bytes)
            written_providers.append(prov)
    except Exception:
        # ロールバック：鍵と共有設定の両方を撤回（部分保存を残さない）
        try:
            store.delete_server_keys(guild_id)
        except Exception:
            pass
        try:
            server_session_manager.clear_shared_auth_config(guild_id)
        except Exception:
            pass
        # 利用者向けメッセージは複雑化を避けるため従来文に統一
        await interaction.followup.send("❌ 共有する認証情報が登録されていません。/ac_auth で登録してください。", ephemeral=True)
        return

    # 表示（鍵は出さない）
    auth = (
        f"🗨️{user_auth['chat']['provider']}/{user_auth['chat']['model']}, "
        f"👀{user_auth['vision']['provider']}/{user_auth['vision']['model']}, "
        f"🖼️{user_auth['imagegen']['provider']}/{user_auth['imagegen']['model']}"
    )
    await interaction.followup.send(redact(f"{warn_prefix}✅ 現在の認証情報［ {auth} ］を共有しました。"), ephemeral=True)
