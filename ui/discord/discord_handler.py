import os
import io
import re
import base64
import aiohttp
import discord
from discord import app_commands, Thread
from discord.ext import commands
from dotenv import load_dotenv
from typing import List, Optional
from pathlib import Path
from datetime import datetime, timezone, timedelta

# セッション/ユーティリティ
from common.session.user_session_manager import user_session_manager
from common.session.server_session_manager import server_session_manager
from common.session.capabilities_loader import load_image_caps, normalize_image_params
from common.utils import thread_utils
from common.utils.thread_utils import remove_thread_from_server, is_thread_managed
from common.utils.websearch_utils import search_web, format_results_as_markdown
from ui.discord.commands.load_commands import load_commands
from ui.discord.discord_thread_context import context_manager

# AI/アクション
from ai.openai.openai_api import call_chatgpt, generate_image_from_prompt
from common.actions.imagegen_action import ImageGenAction
from common.actions.websearch_action import WebSearchAction
from common.actions.webread_action import WebReadAction
from common.actions.webimage_action import WebImageAction

# プロンプトローダ（injection は取得時置換）
from common.session.prompt_loader import (
    load_for_ctx, get_prompt_for_ctx, read_snippet_for_ctx
)

load_dotenv()

# .envから DISCORD_GUILD_ID を読み取り
raw_gid = os.getenv("DISCORD_GUILD_ID", "").strip()
USE_GUILD = bool(raw_gid and not raw_gid.startswith("#"))
GUILD_OBJ = discord.Object(id=int(raw_gid)) if USE_GUILD else None

intents = discord.Intents.all()
intents.members = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
exp_lines = []

SERVICE_NAME = "discord"
ANSI_RE = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')

# ====== ユーティリティ ======
def _chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i+n]
 
class _SafeDict(dict):
    def __missing__(self, k):
        return "{" + k + "}"
 
def _fmt(t: str, **kw) -> str:
    try:
        return (t or "").format_map(_SafeDict(kw))
    except Exception:
        return t or ""

def _print(msg: str, printmsg: bool, expmsg: bool):
    if printmsg:
        print(msg)
    if expmsg:
        exp_lines.append(ANSI_RE.sub('', msg))

def _provider_is_openai(p: str) -> bool:
    return str(p).strip().lower() == "openai"

async def _fetch_reply_source(message: discord.Message) -> Optional[discord.Message]:
    if message.reference and message.reference.message_id:
        if message.reference.cached_message:
            return message.reference.cached_message
        try:
            return await message.channel.fetch_message(message.reference.message_id)
        except Exception:
            pass
    try:
        async for m in message.channel.history(limit=10, before=message.created_at):
            if m.author.id != message.author.id and not m.author.bot:
                return m
    except Exception:
        pass
    return None

def _format_reply_context(src: discord.Message, *, max_chars: int = 800) -> str:
    from datetime import timezone, timedelta
    try:
        from zoneinfo import ZoneInfo
        ts = src.created_at.astimezone(ZoneInfo("Asia/Tokyo")).strftime("%Y-%m-%d %H:%M")
    except Exception:
        ts = (src.created_at.replace(tzinfo=timezone.utc) + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M")

    content = (src.content or "").strip()
    if len(content) > max_chars:
        content = content[:max_chars] + "…"

    urls = []
    if src.content:
        urls += re.findall(r"https?://\S+", src.content)
    urls += [att.url for att in src.attachments if hasattr(att, "url")]

    lines = [
        "[reply_context]",
        f"author: {getattr(src.author, 'display_name', src.author.name)}",
        f"time_jst: {ts}",
        f"jump_url: {src.jump_url}",
        f"content: {content or '(no text)'}",
    ]
    if urls:
        lines.append("links:")
        for u in urls[:8]:
            lines.append(f"- {u}")
    return "\n".join(lines)

# ====== メッセージ処理（AIスレッド） ======
@client.event
async def on_message(message: discord.Message):
    # AIチャットスレッド以外は無視
    thread = message.channel
    if isinstance(thread, Thread):
        guild_id_str = str(message.guild.id)
        if not thread_utils.is_thread_managed(SERVICE_NAME, guild_id_str, thread.id):
            return
    else:
        return

    # スレッドのコンテキスト初期化/追記
    author_name = message.author.display_name
    refid = ""
    if not context_manager.is_initialized(thread.id):
        # ensure_initialized 内で履歴ロード（discord_thread_context.py 側）
        await context_manager.ensure_initialized(thread)
        # 初回の取りこぼし対策：末尾が今回IDでなければ追加
        hist = list(context_manager.get_context(thread.id))
        if not hist or hist[-1].get("id") != str(message.id):
            context_manager.append_context(
                thread.id,
                f"{author_name}: {message.content}",
                str(message.id),
                "",
                message.attachments
            )
    else:
        if message.reference and message.reference.message_id:
            refid = str(message.reference.message_id)
            try:
                # 人間が返信した場合のみ返信元を辿り補完する
                if not message.author.bot:
                    await context_manager.backfill_reply_chain(thread, message, max_hops=10)
            except Exception as e:
                print(f"[reply-chain] backfill failed: {e}")
        context_manager.append_context(
            thread.id,
            f"{author_name}: {message.content}",
            str(message.id),
            refid,
            message.attachments
        )

    # メッセージがボットからのものであれば終了
    if message.author.bot:
        return

    # 認証情報チェック （User > Server > 未登録）
    user_id = message.author.id
    guild_id = message.guild.id
    if not user_session_manager.has_session(user_id):
        if not server_session_manager.has_session(guild_id):
            await message.reply("⚠️ あいちゃぼと会話するには、認証情報を /ac_auth で登録してください。")
            return

    # 認証情報を取得 （User優先）
    if user_session_manager.has_session(user_id):
        auth_data = user_session_manager.get_session(user_id)
    else:
        auth_data = server_session_manager.get_session(guild_id)

    # プロンプトを読み込み（通常は force=False。/ac_auth 直後などは別経路で force=True）
    try:
        load_for_ctx(user_id=user_id, guild_id=guild_id, force=False)
    except Exception as e:
        print(f"[prompt_loader] load_for_ctx failed: {e}")

    # ===== コンテキスト組み立て =====
    context_list = []

    # システム（結合済み / injection は取得時に now_jst 置換）
    try:
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

        system_prompt_text = get_prompt_for_ctx(
            "chat", user_id, guild_id,
            extra_vars = {
                "thread_name": getattr(thread, "name", ""),
                "channel_name": getattr(parent, "name", "") if parent else "",
                "channel_is_nsfw": "true" if (parent_nsfw or thread_nsfw) else "false",
            }
        )
        context_list.append("\s" + system_prompt_text)
    except Exception as e:
        print(f"[prompt_loader] get_prompt_for_ctx failed: {e}")

    # 履歴を積む（今回の発話を重複させない）
    hist = list(context_manager.get_context(thread.id))
    if hist and hist[-1].get("msgid") == str(message.id):
        hist_prev = hist[:-1]
    else:
        hist_prev = hist
    for context in hist_prev:
        context_list.append(context["message"])

    # 返信時のみ、追加ルール（reply_to.txt）＋返信元コンテキスト
    reply_src = None
    if message.reference and message.reference.message_id:
        reply_src = await _fetch_reply_source(message)
    if reply_src:
        reply_to_snippet = read_snippet_for_ctx("reply_to", user_id, guild_id)
        if reply_to_snippet:
            context_list.append("\s" + reply_to_snippet)
        context_list.append(_format_reply_context(reply_src))

    # 最後に今回のユーザー発話（＝応答対象）
    user_text = message.clean_content or message.content or ""
    context_list.append(user_text)

    # オプション
    printmsg = server_session_manager.get_option(guild_id, "printmsg", False)
    expmsg = server_session_manager.get_option(guild_id, "expmsg", False)
    exp_lines.clear()
    trace_tool = server_session_manager.get_option(guild_id, "tracetool", False)
    tool_trace: List[str] = []
    pending_files: List[discord.File] = []

    max_tool_steps = server_session_manager.get_option(guild_id, "max_tool_steps", 10)
    steps = 0
    while True:
        steps += 1

        # オプション -printmsg:on, -expmsg:on 処理
        if printmsg or expmsg:
            _print("context_list =>", printmsg, expmsg)
            for msg in context_list:
                if msg.startswith("\s"):
                    out = msg.replace("\s", "system: ", 1)
                    _print(f"  \033[32m{out}\033[0m", printmsg, expmsg)
                else:
                    _print(f"  \033[33m{msg}\033[0m", printmsg, expmsg)

        # ===== LLM 呼び出し → Action 実行ループ =====
        reply = ""
        for _ in range(2):  # ツール1回まで再試行（必要なら増やす）
            # チャット ==========

            # OpenAIの場合
            if auth_data["chat"]["provider"] == "OpenAI":
                async with message.channel.typing():
                    reply = await call_chatgpt(
                        context_list,
                        auth_data["chat"]["api_key"],
                        auth_data["chat"]["model"],
                        auth_data["chat"].get("max_tokens", 2048)
                    )

            # オプション -printmsg:on, -expmsg:on 処理
            if printmsg or expmsg:
                _print(f"reply => \033[36m{reply}\033[0m", printmsg, expmsg)

            # Action 解析
            action = (
                ImageGenAction.parse(reply)
                or WebSearchAction.parse(reply)
                or WebReadAction.parse(reply)
                or WebImageAction.parse(reply)
            )
            if not action:
                # アクション無し → ループ終端（通常応答）
                break

            # ツール名をトレース用に記録
            tool_name = action.tool
            tool_trace.append(tool_name)

            # オプション -printmsg:on, -expmsg:on 処理
            if (printmsg or expmsg) and action:
                _print(f"action => \033[35m{action.tool}\033[0m", printmsg, expmsg)

            # 画像生成 ==========
            if action.tool == "image.generate":

                # OpenAIの場合
                if _provider_is_openai(auth_data["imagegen"]["provider"]):
                    try:
                        async with message.channel.typing():
                            # ← generate_image_from_prompt は n 非対応なのでループで作成
                            caps = load_image_caps(auth_data["imagegen"]["provider"], auth_data["imagegen"]["model"])
                            n_req, size, quality, warns = normalize_image_params(
                                action, caps,
                                fallback_sizes=["1024x1024"],
                                fallback_max_n=4,
                                fallback_quality=auth_data["imagegen"].get("quality","standard"),
                                passthrough_when_no_caps=True,  # cap無し時は従来通りの“変換なし”
                            )
                            # オプション -printmsg:on, -expmsg:on 処理
                            if printmsg or expmsg:
                                allowed_qualities = caps.get("qualities") or caps.get("allowed_qualities") or []
                                if isinstance(allowed_qualities, str):
                                    allowed_qualities = [allowed_qualities]
                                _print(
                                    "[image.caps] allowed qualities: " + (", ".join(allowed_qualities) if allowed_qualities else "(none)"),
                                    printmsg, expmsg
                                )
                                for w in (warns or []):
                                    _print(f"[image.caps] {w}", printmsg, expmsg)
                            for i in range(n_req):
                                img_bytes = await generate_image_from_prompt(
                                    prompt=action.prompt,
                                    api_key=auth_data["imagegen"]["api_key"],
                                    model=auth_data["imagegen"]["model"],
                                    size=size,
                                    quality=quality,
                                    timeout_sec=90
                                )
                                pending_files.append(
                                    discord.File(fp=io.BytesIO(img_bytes), filename=f"aichabo_image_{i+1}.png")
                                )

                            # 成功メッセージ（実際に生成できた枚数で置換）
                            msg = action.success_message or "画像を{n}枚生成しました。"
                            msg = re.sub(r"\b\d{2,5}\s*x\s*\d{2,5}\b", size, msg)
                            msg += f"\nサイズ: {size}"
                            msg += f"\nプロンプト:\n{action.prompt}"
                            reply = _fmt(
                                msg,
                                n=len(pending_files), size=size
                            )
                            # オプション -printmsg:on, -expmsg:on 処理
                            if printmsg or expmsg:
                                _print(
                                    f"[tool] image.generate ok: count={len(pending_files)} size={size} model={auth_data['imagegen']['model']}",
                                    printmsg, expmsg
                                )

                    except Exception as e:
                        reply = _fmt(action.failure_message or "画像生成に失敗しました：{error}", error=e)

                # オプション -tracetool:on 処理
                if trace_tool:
                    chain = " → ".join(tool_trace + ["response"])
                    print(f"[trace] {chain}")

                break

            # WEB検索 ==========
            if action.tool == "web.search":
                try:
                    async with message.channel.typing():
                        search_results = await search_web(
                            queries=action.queries,
                            top_result=action.top_result,
                            recency_days=action.recency_days,
                            lang=action.lang,
                            region=action.region,
                            timeout=15
                        )
                        if not search_results:
                            result = f"{action.queries} に関する情報は見つかりませんでした。"
                        else:
                            formatted_results = format_results_as_markdown(
                                search_results,
                                require_citations=action.require_citations
                            )
                            result = f"\s{action.queries} の検索結果→{formatted_results}"
                except Exception as e:
                    result = f"{action.queries} の検索中にエラーが発生しました: {e}"

                # 検索結果を会話に追記して、必要ならもう一度 LLM へ
                context_list.append(result)

                # オプション -printmsg:on, -expmsg:on 処理
                if printmsg or expmsg:
                    _print(f"websearch result => \033[35m{result}\033[0m", printmsg, expmsg)

                # ループ継続（次のプロンプトでアクションが返らなくなるまで）
                if steps >= max_tool_steps:
	                # オプション -tracetool:on 処理
                    if trace_tool:
                        chain = " → ".join(tool_trace + ["response(max-step)"])
                        print(f"[trace] {chain}")
                    break
                continue

            # WEB読取 ==========
            if action.tool == "web.read":
                try:
                    async with message.channel.typing():
                        items = await read_urls(
                            action.urls,
                            max_bytes = getattr(action, "max_bytes", 1_500_000) or 1_500_000,
                            max_chars = getattr(action, "max_chars", 20_000) or 20_000,
                            follow_pdfs = getattr(action, "follow_pdfs", True) if hasattr(action, "follow_pdfs") else True,
                            extract_images = getattr(action, "extract_images", True) if hasattr(action, "extract_images") else True,
                            analyze_images = getattr(action, "analyze_images", False) if hasattr(action, "analyze_images") else False,
                            language_hint = getattr(action, "language_hint", None),
                            require_citations = getattr(action, "require_citations", True) if hasattr(action, "require_citations") else True,
                        )
                        formatted = format_read_results_for_llm(
                            items,
                            require_citations = getattr(action, "require_citations", True) if hasattr(action, "require_citations") else True
                        )
                        # systemメッセージとして積む（\s プレフィックス）
                        result = f"\sWEB読み取り結果:\n{formatted}"
                except Exception as e:
                    result = f"web.read の実行中にエラーが発生しました: {e}"
                context_list.append(result)
                # 続行（スキーマが返らなくなるまで）
                if steps >= max_tool_steps:
                    if trace_tool:
                        chain = " → ".join(tool_trace + ["response(max-step)"])
                        print(f"[trace] {chain}")
                    break
                continue

            # 画像解析 ==========
            if action.tool == "web.image":
                try:
                    async with message.channel.typing():
                        # TODO: 実装ポイント
                        # - action.image_urls を Vision API に渡す
                        # - action.questions/tasks をヒントに解析
                        # - 結果文字列を result に格納
                        result = f"\s画像解析対象: {len(action.image_urls)}件（ひな形）"
                except Exception as e:
                    result = f"web.image の実行中にエラーが発生しました: {e}"
                context_list.append(result)
                # 続行
                if steps >= max_tool_steps:
                    if trace_tool:
                        chain = " → ".join(tool_trace + ["response(max-step)"])
                        print(f"[trace] {chain}")
                    break
                continue

        # 不明なツール（将来拡張用） → 終了
        break

    # ===== 通常レスポンス送信 =====
    if reply or pending_files:
        # オプション -printmsg:on, -expmsg:on 処理
        if printmsg or expmsg:
            _print(f"response => {(reply or '').strip()} [attachments={len(pending_files)}]", printmsg, expmsg)
        # モデルの癖で先頭に「 あいちゃぼ: 」が入った場合を除去
        if reply:
            reply = reply.replace("あいちゃぼ: ", "", 1)
        # 添付が10ファイルを超える場合は10ファイルずつ分割送信（1通目に本文を付ける）
        if pending_files:
            first = True
            for chunk in _chunks(pending_files, 10):
                if first:
                    await message.channel.send(content=(reply or None), files=chunk)
                    first = False
                else:
                    await message.channel.send(files=chunk)
        else:
            await message.channel.send(reply)

    # オプション -expmsg:on 処理
    if expmsg:
        try:
            out_dir = Path("common/session/dump")
            out_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d-%H%M%S")
            out_path = out_dir / f"message_{thread.id}_{message.author.id}_{ts}.txt"
            out_path.write_text("\n".join(exp_lines) + "\n", encoding="utf-8", errors="ignore")
        except Exception:
            pass

    # オプション -tracetool:on 処理
    if trace_tool:
        chain = " → ".join(tool_trace + ["response"]) if tool_trace else "response"
        print(f"[trace] {chain}")

    return

# スレッド削除イベント
@client.event
async def on_thread_delete(thread: discord.Thread):
    thread_id = str(thread.id)
    guild_id = str(thread.guild.id)

    if is_thread_managed(SERVICE_NAME, guild_id, thread_id):
        try:
            remove_thread_from_server(SERVICE_NAME, guild_id, thread_id)
            print(f"✅ あいちゃぼの会話対象からスレッド {thread_id} を削除しました。")
        except Exception as e:
            print(f"❌ あいちゃぼの会話対象からスレッド {thread_id} が削除できませんでした: {e}")

# メッセージ変更イベント
@client.event
async def on_message_edit(before, after):
    if before.author.bot:
        return
    print(f"🔄 メッセージが編集されました: {before.author.name} {before.content} ⇒ {after.author.name} {after.content}")
    context_manager.reset_context(before.channel.id)

# メッセージ削除イベント
@client.event
async def on_message_delete(message):
    print(f"❌ メッセージが削除されました: {message.content}")
    context_manager.reset_context(message.channel.id)

# ====== 起動/同期 ======
@client.event
async def on_ready():
    print(f"✅ {client.user} としてログインしました。(Ctrl-Cで終了します)")

    try:
        load_commands(tree, client, GUILD_OBJ)
        for cmd in tree.get_commands():
            print(f"🔍 コマンド登録: /{cmd.name}")
        if USE_GUILD:
            await tree.sync(guild=GUILD_OBJ)
            print(f"🧪 開発モード（サーバーID={raw_gid}）でコマンドを同期しました")
        else:
            await tree.sync()
            print("🚀 本番モード（グローバル）でコマンドを同期しました")

        # 参加していないサーバーの検出とクリーニング（サーバーID単位）
        existing_server_ids = {str(guild.id) for guild in client.guilds}
        thread_utils.clean_deleted_servers(SERVICE_NAME, existing_server_ids)

        # すべてのサーバー（Guild）に対して処理
        for guild in client.guilds:
            server_id = str(guild.id)
            thread_ids = set()

            # チャンネルごとのアーカイブ済みスレッド
            for channel in guild.text_channels:
                for thread in channel.threads:
                    thread_ids.add(str(thread.id))

            # スレッド存在チェック用に記憶されたスレッド一覧をクリーンアップ
            thread_utils.clean_deleted_threads(SERVICE_NAME, server_id, thread_ids)

        print("✅ 存在しないサーバー/スレッドのチェックおよびクリーンアップを完了しました")

    except Exception as e:
        print(f"❌ コマンド同期に失敗しました: {e}")
        await client.close()

# ===== Bot 起動 =====
def start_discord_bot():
    client.run(os.environ["DISCORD_BOT_TOKEN"])
