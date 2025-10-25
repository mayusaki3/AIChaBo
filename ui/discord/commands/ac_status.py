# ui/discord/commands/ac_status.py
# ------------------------------------------------------------
# /ac_status: 使用中のあいちゃぼの状態を表示
# - オプションパラメータで、サーバー単位でシステム変数を設定可
# - システム変数は、サーバーセッションマネージャーで管理
# - システム変数は、各処理でトレースログONなど、デバッグ用に使用
# - システム変数名に規定はなく、指定した名前で自由に設定可能
# ------------------------------------------------------------
import inspect
import discord
from pathlib import Path
from datetime import datetime
from discord import app_commands, Interaction, Thread
from common.session.user_session_manager import user_session_manager
from common.session.server_session_manager import server_session_manager
from common.session.prompt_loader import (
    load_for_ctx,
    export_for_ctx,
    AuthNotConfigured,
)
from common.utils.intent import clear_intent_caches, build_tool_hint_from_config
from common.utils.thread_utils import is_thread_managed
from ui.discord.discord_thread_context import context_manager

HELP_TEXT = {
    "usage": "/ac_status <option>",
    "description": "使用中のあいちゃぼの状態を表示します。"
}

SERVICE_NAME = "discord"

# オプションの解析
def _parse_option_tokens(option: str | None) -> list[tuple[str, str, bool | None]]:
    # 返り値: [("set"|"get", key, value_or_None), ...]
    #   - "-foo:on"  -> ("set", "foo", True)
    #   - "-foo:off" -> ("set", "foo", False)
    #   - "-foo"     -> ("get", "foo", None)
    #   - "-showopt" -> ("get", "_list", None)
    out: list[tuple[str, str, bool | None]] = []
    if not option:
        return out
    for tok in option.split():
        tok = tok.strip()
        if not tok.startswith("-"):
            continue
        body = tok[1:]
        if body.lower() == "showopt":
            out.append(("get", "_list", None))
            continue
        if ":" in body:
            key, val = body.split(":", 1)
            key = key.strip().lower()
            val = val.strip().lower()
            if val in ("on", "off"):
                out.append(("set", key, val == "on"))
        else:
            out.append(("get", body.strip().lower(), None))
    return out

# 非同期処理
async def _maybe_await(result):
    return await result if inspect.isawaitable(result) else result

def get_command():
    return app_commands.Command(
        name="ac_status",
        description=HELP_TEXT["description"],
        callback=ac_status_command,
    )
@app_commands.describe(option="オプション: ")
async def ac_status_command(interaction: Interaction, option: str = None):
    await interaction.response.defer(thinking=True, ephemeral=True)

    thread = interaction.channel
    msg_lines: list[str] = []

    # スレッド管理状況
    managed = False
    if isinstance(thread, Thread):
        # スレッドIDでスレッド情報取得（存在しない場合は None）
        if not is_thread_managed(SERVICE_NAME, str(interaction.guild_id), thread.id):
            msg_lines.append("ℹ️ このスレッドであいちゃぼと会話するには /ac_invite であいちゃぼを招待してください。")
        else:
            managed = True
    else:
        msg_lines.append("ℹ️ あいちゃぼとの会話はスレッド内でのみ利用できます。")

    # 共有されたユーザー認証情報の状態
    guild = interaction.guild
    guild_id = interaction.guild.id
    shared = server_session_manager.get_shared_auth_config(guild_id)
    if shared:
        sharing_user_id = shared.get("shared_by_user_id")
        user_name = f"id: {sharing_user_id}" if sharing_user_id else "（共有者不明）"
        try:
            member = guild.get_member(sharing_user_id) or await guild.fetch_member(sharing_user_id) if sharing_user_id else None
            if member: user_name = member.display_name
        except Exception:
            pass
        try:
            auth = (
                f"🗨️{shared['chat']['provider']}/{shared['chat']['model']}, "
                f"👀{shared['vision']['provider']}/{shared['vision']['model']}, "
                f"🖼️{shared['imagegen']['provider']}/{shared['imagegen']['model']}"
            )
            msg_lines.append(f"ℹ️ {user_name} さんの認証情報［ {auth} ］が共有されています。")
        except Exception:
            msg_lines.append(f"ℹ️ {user_name} さんの認証情報が共有されています。")

    # ユーザー認証情報の確認
    user_id = interaction.user.id
    user_auth = user_session_manager.get_session(user_id)
    if user_auth:
        auth = (
            f"🗨️{user_auth['chat']['provider']}/{user_auth['chat']['model']}, "
            f"👀{user_auth['vision']['provider']}/{user_auth['vision']['model']}, "
            f"🖼️{user_auth['imagegen']['provider']}/{user_auth['imagegen']['model']}"
        )
        msg_lines.append(f"🧑‍💻 現在の認証情報［ {auth} ］")
    else:
        if not server_auth:
            msg_lines.append("⚠️ あいちゃぼと会話するには /ac_auth で認証情報を登録してください。")

    # オプション処理
    tokens = _parse_option_tokens(option)
    opt_msgs: list[str] = []
    for kind, key, val in tokens:
        if kind == "set":
            server_session_manager.set_option(guild_id, key, bool(val))
        elif kind == "get":
            if key == "_list":
                all_opts = server_session_manager.all_options(guild_id)
                if all_opts:
                    pairs = "、".join([f"-{k}:{'on' if v else 'off'}" for k, v in sorted(all_opts.items())])
                    opt_msgs.append(f"🔎 現在のオプション: {pairs}")
                else:
                    opt_msgs.append("🔎 設定済みのオプションはありません。")
    if opt_msgs:
        msg_lines.extend(opt_msgs)

    # AIチャットスレッドのコンテキスト状態
    if managed:
        if not context_manager.is_initialized(thread.id):
            await context_manager.ensure_initialized(thread)
        context = context_manager.get_context(thread.id)
        if context:
            msg_lines.append(f"📜 スレッドのコンテキスト履歴は {len(context)} 件あります。")
            if option == "d":
                msg_lines.append("")
                msg_lines.append("📜 コンテキスト履歴:")
                for mm in context:
                    msg_lines.append(f"🟡{mm['message']}")
                    msg_lines.append(f"   - Id: {mm['msgid']}, Ref: {mm['refid']}")
                    msg_lines.append(f"   - Attachment: {mm['attachments']}")
        else:
            msg_lines.append("📜 スレッドのコンテキスト履歴はありません。")

    # option処理: -expall オプション, -exp オプション
    export_msgs: list[str] = []
    flags = option.split() if option else []
    if "-expall" in flags:
        try:
            res = await _maybe_await(context_manager.export_all_contexts())
            # res が dict の場合のヒント処理
            if isinstance(res, dict):
                count = res.get("count", 0)
                outdir = res.get("dir", "common/session/dump")
                export_msgs.append(f"🗂️ 全スレッド（{count} 件）のコンテキスト履歴を `{outdir}` にエクスポートしました。")
            else:
                export_msgs.append("🗂️ 全スレッドのコンテキスト履歴をエクスポートしました。")
        except Exception as e:
            export_msgs.append(f"❌ 全スレッドのエクスポートに失敗しました: {e}")
    elif "-exp" in flags:
        if isinstance(thread, Thread):
            try:
                res = await _maybe_await(context_manager.export_context(thread.id))
                if isinstance(res, dict):
                    path = res.get("path", "")
                    export_msgs.append(f"💾 このスレッドのコンテキスト履歴をエクスポートしました。{f'`{path}`' if path else ''}")
                else:
                    export_msgs.append("💾 このスレッドのコンテキスト履歴をエクスポートしました。")
            except Exception as e:
                export_msgs.append(f"❌ このスレッドのエクスポートに失敗しました: {e}")
        else:
            export_msgs.append("⚠️ スレッド外では `-exp` は使用できません。")

    # option処理: -loadprompt / -expprompt / -loadintent / -expintent オプション
    if "-loadprompt" in flags:
        try:
            # ユーザー＞サーバー優先で認証を解決して、chat/vision/image を再構築＆キャッシュ
            load_for_ctx(user_id=user_id, guild_id=guild_id, force=True)
            export_msgs.append("🔄 プロンプト/スキーマを再読み込みしました。")
        except AuthNotConfigured:
            export_msgs.append("⚠️ 認証情報が未設定のためプロンプト/スキーマは無効です。")

    if "-expprompt" in flags:
        out_dir = Path("common/session/dump")
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        fname = f"system_prompts_all_{guild_id or 'dm'}_{user_id}_{ts}.txt"
        out_path = out_dir / fname

        blocks: list[str] = []

        # チャット用プロンプト
        roles = [("chat","CHAT_PROMPT")]
        for role, label in roles:
            extra = None
            # スレッド内で実行された場合のみ、thread_name を注入
            if isinstance(thread, Thread):
                def _nsfw_flag(obj) -> bool:
                    try:
                        if obj is None:
                            return False
                        if hasattr(obj, "nsfw"):  # TextChannel など
                            return bool(getattr(obj, "nsfw"))
                        if hasattr(obj, "is_nsfw"):  # メソッドの場合
                            f = getattr(obj, "is_nsfw")
                            return bool(f() if callable(f) else f)
                    except Exception:
                        pass
                    return False

                parent = getattr(thread, "parent", None)
                parent_nsfw = _nsfw_flag(parent)
                thread_nsfw = _nsfw_flag(thread)
                extra = {
                    "thread_name": thread.name,
                    "channel_name": getattr(parent, "name", "") if parent else "",
                    "channel_is_nsfw": "true" if (parent_nsfw or thread_nsfw) else "false",
                }
            data = export_for_ctx(role=role, user_id=user_id, guild_id=guild_id, extra_vars=extra)
            text = data.decode("utf-8", errors="ignore") if data else ""
            blocks.append(f"==== [{label}] ====\n{text}")

        # 返信用（reply_to.txt）
        try:
            from common.session.prompt_loader import read_snippet_for_ctx
            reply_to = read_snippet_for_ctx("reply_to", user_id, guild_id) or ""
            blocks.append("==== [REPLY_TO_PROMPT] reply_to.txt ====\n" + reply_to)
        except Exception:
            pass

        # 要約用（summary.txt）
        try:
            from common.session.prompt_loader import read_snippet_for_ctx
            summary_snip = read_snippet_for_ctx("summary", user_id, guild_id) or ""
            blocks.append("==== [SUMMARY_PROMPT] summary.txt ====\n" + summary_snip)
        except Exception:
            pass

        merged = "\n\n".join(blocks)
        out_path.write_text(merged, encoding="utf-8")

        suffix = "（空ファイル）" if not merged.strip() else ""
        export_msgs.append(f"📝 現在使用しているプロンプト/スキーマをエクスポートしました。")

    if "-loadintent" in flags:
        try:
            clear_intent_caches()
            export_msgs.append("🔄 インテントYAMLを再読み込みしました。")
        except Exception as e:
            export_msgs.append(f"❌ インテントYAMLの再読み込みに失敗しました: {e}")

    if "-expintent" in flags:
        try:
            out_dir = Path("common/session/dump")
            out_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d-%H%M%S")
            # intents/ と dictionaries/ をそのまま複製（読み取り→1ファイルに連結）
            cfg_root = Path("common/config")
            bundle_path = out_dir / f"intent_bundle_{ts}.txt"
            parts: list[str] = []
            for sub in ("intents", "dictionaries"):
                p = cfg_root / sub
                if not p.exists():
                    continue
                parts.append(f"==== [{sub}] ====")
                for y in sorted(p.glob("**/*.yaml")):
                    try:
                        txt = y.read_text(encoding="utf-8", errors="ignore")
                        parts.append(f"-- {y} --\n{txt}\n")
                    except Exception as ee:
                        parts.append(f"-- {y} --\n<read error: {ee}>\n")
            bundle_path.write_text("\n".join(parts), encoding="utf-8")
            export_msgs.append(f"🗂️ インテント定義を `{bundle_path}` にエクスポートしました。")
        except Exception as e:
            export_msgs.append(f"❌ インテント定義のエクスポートに失敗しました: {e}")

    if export_msgs:
        msg_lines.append("")
        msg_lines.extend(export_msgs)

    await interaction.followup.send("\n".join(msg_lines), ephemeral=True)
