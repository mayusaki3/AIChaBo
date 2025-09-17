import os
import io
import re
import discord
from discord import app_commands, Thread
from dotenv import load_dotenv
from typing import List, Optional, Callable, Tuple, Awaitable
from pathlib import Path
from datetime import datetime

# セッション/ユーティリティ
from common.session.user_session_manager import user_session_manager
from common.session.server_session_manager import server_session_manager
from common.session.capabilities_loader import load_image_caps, normalize_image_params
from common.utils import thread_utils
from common.utils.thread_utils import remove_thread_from_server, is_thread_managed
from common.utils.websearch_utils import search_web, format_results_as_markdown
from common.utils.webread_utils import read_urls, format_read_results_for_llm
from common.utils.attachments import split_attachments, render_append_block
from common.utils.prefetch import prefetch_doc_summaries
from common.utils.intent import (
    build_tool_hint_auto,
    detect_intent,
    build_fallback_queries,
    get_search_defaults,
    extract_from_read,  # 追加
)
from ui.discord.commands.load_commands import load_commands
from ui.discord.discord_thread_context import context_manager
from ui.discord.discord_attachments import from_discord_attachments

# AI/アクション
from ai.openai.openai_api import call_chatgpt, analyze_openai_vision, generate_image_from_prompt
from ai.gemini.gemini_api import call_gemini_chat, analyze_gemini_vision, generate_gemini_image
from ai.claude.claude_api import call_claude_chat, analyze_claude_vision

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
DISCORD_MSG_LIMIT = 2000

# ====== ユーティリティ ======

# provider -> 画像生成関数マップ（bytes を返す関数）
IMAGEGEN_GENERATORS: dict[str, Callable[..., Awaitable[bytes]]] = {
    "OpenAI": generate_image_from_prompt,   # 既存
    "Gemini": generate_gemini_image,        # 既存
    # "Claude": 画像生成は非対応（エラーを返す or マップしない）
}

async def _run_imagegen_common(
    *, provider: str, api_key: str, model: str,
    action,  # ImageGenAction
    imagegen_cfg: dict,
    printmsg: bool, expmsg: bool
) -> Tuple[str, list[discord.File]]:
    """
    capabilities を読み、n/size/quality を正規化 → 画像を n 枚生成 → 成功メッセージを返す。
    戻り値: (reply_message, files)
    例外は上位で握る（既存の try/except に任せる）。
    """
    caps = load_image_caps(provider, model)
    n_req, size, quality, warns = normalize_image_params(
        action, caps,
        fallback_sizes=["1024x1024"],
        fallback_max_n=4,
        fallback_quality=imagegen_cfg.get("quality", "standard"),
        passthrough_when_no_caps=True,
    )

    # ログ（任意）
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

    gen_fn = IMAGEGEN_GENERATORS.get(provider)
    if not gen_fn:
        # Claude など未対応
        raise RuntimeError(f"画像生成は {provider} では未対応です。")

    files: list[discord.File] = []
    for i in range(n_req):
        img_bytes = await gen_fn(
            prompt=action.prompt,
            api_key=api_key,
            model=model,
            size=size,
            quality=quality,
            timeout_sec=90
        )
        files.append(discord.File(fp=io.BytesIO(img_bytes), filename=f"aichabo_image_{i+1}.png"))

    # 成功メッセージ生成（既存ロジックをそのまま共通化）
    msg = action.success_message or "画像を{n}枚生成しました。"
    # 表示用にサイズ文字（例: 1024x1024）を埋め込み
    import re as _re
    msg = _re.sub(r"\b\d{2,5}\s*x\s*\d{2,5}\b", size, msg)
    msg += f"\nサイズ: {size}"
    msg += f"\nプロンプト:\n{action.prompt}"
    reply = _fmt(msg, n=len(files), size=size)

    return reply, files

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

def _split_for_discord(text: str, limit: int = DISCORD_MSG_LIMIT) -> list[str]:
    """Discordの本文上限に合わせて安全に分割（簡易にコードブロックも保護）"""
    if not text:
        return []
    if len(text) <= limit:
        return [text]

    chunks, buf, in_code = [], "", False
    for line in text.splitlines(keepends=True):
        # コードブロック境界検出
        if line.strip().startswith("```"):
            fence = True
        else:
            fence = False

        # 追加したらオーバーする？
        if len(buf) + len(line) > limit:
            # 開いたままなら一旦閉じて送る
            if in_code:
                to_send = buf + ("```" if not buf.rstrip().endswith("```") else "")
                chunks.append(to_send[:limit])
                buf = "```"  # 次の塊は再オープンから
            else:
                chunks.append(buf)
                buf = ""
        buf += line

        # フェンスでトグル
        if fence:
            in_code = not in_code

    if buf:
        # 最終チャンクの閉じ忘れ防止
        if in_code and not buf.rstrip().endswith("```"):
            buf += "\n```"
        chunks.append(buf)

    # 念のため二段階で長すぎる塊を切る（非常時）
    out = []
    for c in chunks:
        if len(c) <= limit:
            out.append(c)
        else:
            for i in range(0, len(c), limit):
                out.append(c[i:i+limit])
    return out

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
    atts = from_discord_attachments(message.attachments)
    imgs, docs = split_attachments(atts)
    if not context_manager.is_initialized(thread.id):
        # ensure_initialized 内で履歴ロード（discord_thread_context.py 側）
        await context_manager.ensure_initialized(thread)
        # 初回の取りこぼし対策：末尾が今回IDでなければ追加
        hist = list(context_manager.get_context(thread.id))
        if not hist or hist[-1].get("msgid") != str(message.id):
            user_text = f"{author_name}: {message.content}" + render_append_block(imgs, docs)
            context_manager.append_context(thread.id, user_text, str(message.id), "", None)
    else:
        if message.reference and message.reference.message_id:
            refid = str(message.reference.message_id)
            try:
                # 人間が返信した場合のみ返信元を辿り補完する
                if not message.author.bot:
                    await context_manager.backfill_reply_chain(thread, message, max_hops=10)
            except Exception as e:
                print(f"[reply-chain] backfill failed: {e}")
        user_text = f"{author_name}: {message.content}" + render_append_block(imgs, docs)
        context_manager.append_context(thread.id, user_text, str(message.id), refid, None)

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
    user_text += render_append_block(imgs, docs)
    context_list.append(user_text)

    # ---- 前ターンの raw URL を持ち越さない（誤検出防止）----
    try:
        context_manager.set_meta(thread.id, "last_webread_urls", tuple())
    except Exception:
        pass

    # 非画像添付がある場合は、LLM を呼ぶ前に先に web.read 相当の読取りを実行し、
    # 要約を \s（system）として文脈に積む。二重実行防止のため signature でガード。
    if docs:
        doc_urls = [d.url for d in docs if d.url]
        if doc_urls:
            formatted, sig = await prefetch_doc_summaries(doc_urls)
            if formatted and sig:
                last_sig = context_manager.get_meta(thread.id, "last_attached_doc_sig")
                if last_sig != sig:
                    context_list.append("\\s 添付ファイルの内容プレビュー:\n" + formatted)
                    context_manager.set_meta(thread.id, "last_attached_doc_sig", sig)

    # 検索ヒントを \s で注入（LLMに web.search を確実に思い出させる）
    hint = build_tool_hint_auto(user_text, locale="ja")
    if hint:
        context_list.append("\\s " + hint)

    # ---- GitHub Repo URL が含まれる場合は /repos と /git/trees を先読み（LLMに依存せず確実化）----
    try:
        intent_name_prefetch = detect_intent(user_text, locale="ja") or ""
        if intent_name_prefetch == "github":
            m = re.search(r"https?://github\\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)(?:/(?:tree|blob)/([A-Za-z0-9._/-]+))?", user_text)
            if m:
                owner_repo, user_ref = m.group(1), (m.group(2) or "").strip()
                if user_ref and "/" in user_ref:
                    user_ref = user_ref.split("/", 1)[0]
                sig = (owner_repo, user_ref)
                last_sig = context_manager.get_meta(thread.id, "gh_prefetch_sig")
                if last_sig != sig:
                    async with message.channel.typing():
                        # --- 1st: /repos + /branches を取得して実在ブランチを把握 ---
                        meta_urls = [
                            f"https://api.github.com/repos/{owner_repo}",
                            f"https://api.github.com/repos/{owner_repo}/branches?per_page=100",
                        ]
                        token = os.getenv("GITHUB_TOKEN")
                        headers = {"Authorization": f"Bearer {token}"} if token else None
                        items_meta = await read_urls(
                            meta_urls,
                            max_bytes = 1_500_000,
                            max_chars = 20_000,
                            follow_pdfs = True,
                            extract_images = True,
                            analyze_images = False,
                            language_hint = None,
                            require_citations = True,
                            headers = headers,
                        )
                        # 既読URLを保持
                        last_urls = [it.get("url") for it in items_meta if isinstance(it, dict) and it.get("url")]
                        # ブランチ名の抽出
                        import json
                        branches = set()
                        default_branch = None
                        for it in items_meta:
                            u = it.get("url") or ""
                            body = it.get("raw") or it.get("text") or it.get("summary") or ""
                            # summary(コードフェンス)しか無い場合に備えてJSONっぽく整形
                            if body.startswith("```"):
                                import re as _re
                                body = _re.sub(r"^```[a-zA-Z]*\n", "", body)
                                body = _re.sub(r"\n```$", "", body)
                            try:
                                obj = json.loads(body)
                            except Exception:
                                obj = None
                            if "repos/" in u and obj and isinstance(obj, dict):
                                default_branch = obj.get("default_branch") or default_branch
                            if "/branches" in u and isinstance(obj, list):
                                for b in obj:
                                    name = (b.get("name") or "").strip()
                                    if name:
                                        branches.add(name)
                        # 候補順の決定（ユーザー指定 > default > よくある名前 > その他）
                        preferred = ["develop", "main", "master", "trunk"]
                        order = []
                        if user_ref: order.append(user_ref)
                        if default_branch: order.append(default_branch)
                        order += [b for b in preferred if b in branches]
                        order += sorted(branches - set(order))
                        # --- 2nd: 上位候補（最大2〜3）について Tree を取得 ---
                        tree_urls = [
                            f"https://api.github.com/repos/{owner_repo}/git/trees/{r}?recursive=1"
                            for r in order[:3]
                        ]
                        items_tree = []
                        if tree_urls:
                            items_tree = await read_urls(
                                tree_urls,
                                max_bytes = 1_500_000,
                                max_chars = 20_000,
                                follow_pdfs = True,
                                extract_images = True,
                                analyze_images = False,
                                language_hint = None,
                                require_citations = True,
                                headers = headers,
                            )
                        # --- 3rd: Tree → raw へ自動フォローアップ（同ターン最大8件）
                        prefetch_used_fallback = True
                        try:
                            import json as _json
                            TARGET_EXTS = {"py","js","ts","tsx","jsx","go","rs","java","kt","c","cpp","h","hpp","cs",
                                        "yaml","yml","toml","json","ini","cfg","conf","md","mdx","rst","adoc",
                                        "sh","zsh","bash","bat","ps1","ipynb"}
                            EXCLUDE_DIRS = ("node_modules/","dist/","build/","venv/",".venv/","__pycache__/",".git/")
                            SPECIAL = {"Dockerfile","docker-compose.yml","docker-compose.yaml","Makefile","CMakeLists.txt"}

                            def _ok_path(p: str, size: int) -> bool:
                                if any(seg in p for seg in EXCLUDE_DIRS): return False
                                if size and size > 300_000: return False
                                base = p.rsplit("/",1)[-1]
                                if base in SPECIAL: return True
                                if "." in base:
                                    ext = base.rsplit(".",1)[-1].lower()
                                    if ext in TARGET_EXTS and not base.endswith((".min.js",".bundle.js",".map")):
                                        return True
                                return False

                            # owner_repo / ref は tree_urls から復元
                            owner_repo, ref = None, None
                            for u in tree_urls:
                                m = re.search(r"api\\.github\\.com/repos/([^/]+/[^/]+)/git/trees/([^?]+)", u)
                                if m:
                                    owner_repo, ref = m.group(1), m.group(2)
                                    break

                            candidates = []
                            for it in items_tree:
                                u = it.get("url","")
                                if "api.github.com/repos/" in u and "/git/trees/" in u:
                                    txt = it.get("raw") or it.get("text") or it.get("summary") or ""
                                    try:
                                        obj = _json.loads(txt)
                                        for node in obj.get("tree", []):
                                            if node.get("type") != "blob":
                                                continue
                                            p = node.get("path","")
                                            size = int(node.get("size") or 0)
                                            if _ok_path(p, size):
                                                candidates.append((p, size))
                                    except Exception:
                                        pass

                            candidates = sorted(set(candidates), key=lambda t: (t[0].count("/"), t[1] or 0))[:8]
                            raw_urls = [f"https://raw.githubusercontent.com/{owner_repo}/{ref}/{p}" for p,_ in candidates] if (owner_repo and ref) else []

                            if raw_urls:
                                # 認証ヘッダ（あれば）
                                token = os.getenv("GITHUB_TOKEN")
                                headers2 = {"Authorization": f"Bearer {token}"} if token else None

                                items_raw = await read_urls(
                                    raw_urls,
                                    max_bytes=1_500_000, max_chars=20_000,
                                    follow_pdfs=True, extract_images=True, analyze_images=False,
                                    language_hint=None, require_citations=True,
                                    headers=headers2,
                                )
                                # 既存まとめにマージし、文脈に積む
                                items_all = items_meta + items_tree + items_raw
                                formatted = format_read_results_for_llm(items_all, require_citations=True)
                                last_urls.extend([it.get("url") for it in items_raw if isinstance(it, dict) and it.get("url")])
                                try:
                                    context_manager.set_meta(thread.id, "last_webread_urls", tuple(last_urls))
                                    context_manager.set_meta(thread.id, "gh_prefetch_sig", sig)
                                except Exception:
                                    pass
                                context_list.append("\\s GitHub API 取得(raw):\n" + formatted)
                                prefetch_used_fallback = False
                            else:
                                # raw が拾えなかった場合は従来どおり
                                items_all = items_meta + items_tree
                                formatted = format_read_results_for_llm(items_all, require_citations=True)
                        except Exception as e:
                            if server_session_manager.get_option(guild_id, "printmsg", False):
                                print(f"[prefetch][github raw follow-up skipped] {e}")
                        # raw まで行けた場合は重複追記を避ける
                        if prefetch_used_fallback:
                            items_all = items_meta + items_tree
                            formatted = format_read_results_for_llm(items_all, require_citations=True)
                            last_urls.extend([it.get("url") for it in items_tree if isinstance(it, dict) and it.get("url")])
                            try:
                                context_manager.set_meta(thread.id, "last_webread_urls", tuple(last_urls))
                                context_manager.set_meta(thread.id, "gh_prefetch_sig", sig)
                            except Exception:
                                pass
                            context_list.append("\\s GitHub API 取得:\n" + formatted)
    except Exception as e:
        if server_session_manager.get_option(guild_id, "printmsg", False):
            print(f"[prefetch][github] skipped: {e}")

    # オプション
    printmsg = server_session_manager.get_option(guild_id, "printmsg", False)
    expmsg = server_session_manager.get_option(guild_id, "expmsg", False)
    exp_lines.clear()
    trace_tool = server_session_manager.get_option(guild_id, "tracetool", False)
    tool_trace: List[str] = []
    pending_files: List[discord.File] = []

    max_tool_steps = server_session_manager.get_option(guild_id, "max_tool_steps", 10)
    while True:

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
        tool_runs = 0
        while tool_runs < max_tool_steps:
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

            # Geminiの場合
            elif auth_data["chat"]["provider"] == "Gemini":
                async with message.channel.typing():
                    reply = await call_gemini_chat(
                        context_list,
                        auth_data["chat"]["api_key"],
                        auth_data["chat"]["model"],
                        auth_data["chat"].get("max_tokens", 2048)
                    )

            # Claudeの場合
            elif auth_data["chat"]["provider"] == "Claude":
                async with message.channel.typing():
                    reply = await call_claude_chat(
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
                try:
                    async with message.channel.typing():
                        provider = auth_data["imagegen"]["provider"]
                        model    = auth_data["imagegen"]["model"]
                        api_key  = auth_data["imagegen"]["api_key"]
                        reply, new_files = await _run_imagegen_common(
                            provider=provider,
                            api_key=api_key,
                            model=model,
                            action=action,
                            imagegen_cfg=auth_data["imagegen"],
                            printmsg=printmsg, expmsg=expmsg
                        )
                        pending_files.extend(new_files)
                        if printmsg or expmsg:
                            _print(f"[tool] image.generate ok: count={len(new_files)} size={new_files and 'see msg'} model={model}",
                                   printmsg, expmsg)
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
                        # YAMLのsearch_defaultsを補完注入（LLMが未指定でも安定）
                        intent_name = detect_intent(user_text, locale="ja") or ""
                        defaults = get_search_defaults(intent_name, locale="ja") if intent_name else {}
                        top_result = action.top_result or defaults.get("top_result", 5)
                        region = action.region or defaults.get("region")
                        recency_days = action.recency_days if action.recency_days is not None else defaults.get("recency_days")

                        search_results = await search_web(
                            queries=action.queries,
                            top_result=top_result,
                            recency_days=recency_days,
                            lang=action.lang,
                            region=region,
                            timeout=15
                        )
                        if not search_results:
                            # --- YAML定義による汎用フォールバック ---
                            intent_name = intent_name or detect_intent(user_text, locale="ja") or ""
                            if intent_name:
                                dedup, recency_override = build_fallback_queries(intent_name, action.queries, locale="ja")
                                try:
                                    search_results = await search_web(
                                        queries=dedup,
                                        top_result=top_result,
                                        recency_days=recency_override,  # YAMLが指定すれば上書き
                                        region=region or "jp-jp",
                                        require_citations=True,
                                    )
                                except Exception:
                                    search_results = []
                                if search_results:
                                    formatted_results = format_results_as_markdown(search_results, require_citations=True)
                                    q_preview = ", ".join(dedup[:2]) + (f" 他{len(dedup)-2}件" if len(dedup) > 2 else "")
                                    result = f"\\s[{q_preview}] の検索結果→{formatted_results}"
                                else:
                                    q_preview = ", ".join(dedup[:2]) + (f" 他{len(dedup)-2}件" if len(dedup) > 2 else "")
                                    result = f"[{q_preview}] に関する情報は見つかりませんでした。"
                            else:
                                q_preview = ", ".join(action.queries[:2]) + (f" 他{len(action.queries)-2}件" if len(action.queries) > 2 else "")
                                result = f"[{q_preview}] に関する情報は見つかりませんでした。"
                        else:
                            formatted_results = format_results_as_markdown(
                                search_results,
                                require_citations=action.require_citations
                            )
                            q_preview = ", ".join(action.queries[:2])
                            if len(action.queries) > 2:
                                q_preview += f" 他{len(action.queries)-2}件"
                            result = f"\\s[{q_preview}] の検索結果→{formatted_results}"
                except Exception as e:
                    q_preview = ", ".join(action.queries[:2]) + (f" 他{len(action.queries)-2}件" if len(action.queries) > 2 else "")
                    result = f"[{q_preview}] の検索中にエラーが発生しました: {e}"

                # 検索結果を会話に追記して、必要ならもう一度 LLM へ
                context_list.append(result)

                # オプション -printmsg:on, -expmsg:on 処理
                if printmsg or expmsg:
                    _print(f"websearch result => \033[35m{result}\033[0m", printmsg, expmsg)
                # 続行
                tool_runs += 1
                if tool_runs >= max_tool_steps:
                    if trace_tool:
                        chain = " → ".join(tool_trace + ["response(max-step)"])
                        print(f"[trace] {chain}")
                    break
                continue

            # WEB読取 ==========
            if action.tool == "web.read":
                try:
                    async with message.channel.typing():
                        # （将来）Actionから渡されたHTTPヘッダを read_urls に橋渡し
                        extra_headers = getattr(action, "headers", None) if hasattr(action, "headers") else None
                        if not extra_headers and detect_intent(user_text, locale="ja") == "github":
                            token = os.getenv("GITHUB_TOKEN")  # もしくは auth_data["github"]["token"]
                            if token:
                                extra_headers = {"Authorization": f"Bearer {token}"}

                        # --- LLM生成URLのサニタイズ: GitHub Tree API で /repos 抜けを補正 ---
                        def _fix_github_urls(urls):
                            fixed = []
                            for u in (urls or []):
                                if isinstance(u, str):
                                    # Tree API なのに /repos/ が欠けている誤URLを補正
                                    if u.startswith("https://api.github.com/") and "/git/trees/" in u and "/repos/" not in u:
                                        u = u.replace("https://api.github.com/", "https://api.github.com/repos/", 1)
                                fixed.append(u)
                            return fixed

                        action_urls = getattr(action, "urls", None) if hasattr(action, "urls") else None
                        if action_urls:
                            action.urls = _fix_github_urls(action_urls)
                        items = await read_urls(
                            action.urls,
                            max_bytes = getattr(action, "max_bytes", 1_500_000) or 1_500_000,
                            max_chars = getattr(action, "max_chars", 20_000) or 20_000,
                            follow_pdfs = getattr(action, "follow_pdfs", True) if hasattr(action, "follow_pdfs") else True,
                            extract_images = getattr(action, "extract_images", True) if hasattr(action, "extract_images") else True,
                            analyze_images = getattr(action, "analyze_images", False) if hasattr(action, "analyze_images") else False,
                            language_hint = getattr(action, "language_hint", None),
                            require_citations = getattr(action, "require_citations", True) if hasattr(action, "require_citations") else True,
                            headers = extra_headers,
                        )
                        formatted = format_read_results_for_llm(
                            items,
                            require_citations = getattr(action, "require_citations", True) if hasattr(action, "require_citations") else True
                        )
                        # 直近の web.read URL（監査/ガード用に保持）
                        last_urls = [it.get("url") for it in items if isinstance(it, dict) and it.get("url")]
                        try:
                            context_manager.set_meta(thread.id, "last_webread_urls", tuple(last_urls))
                        except Exception:
                            pass
                        # --- GitHub: Tree→raw の自動フォローアップ（同ターン最大8件） ---
                        try:
                            intent_name = detect_intent(user_text, locale="ja") or ""
                            if intent_name == "github":
                                sources = [u for u in last_urls if isinstance(u, str)]
                                has_tree = any(("api.github.com/repos/" in u and "/git/trees/" in u) for u in sources)
                                has_raw  = any(("raw.githubusercontent.com" in u) for u in sources)
                                if has_tree and not has_raw:
                                    import re, json
                                    # 1) owner_repo/ref を Tree API のURLから決定
                                    owner_repo, ref = None, None
                                    for u in sources:
                                        m = re.search(r"api\\.github\\.com/repos/([^/]+/[^/]+)/git/trees/([^?]+)", u)
                                        if m:
                                            owner_repo, ref = m.group(1), m.group(2)
                                            break
                                    # 2) Tree JSON から候補pathを抽出
                                    TARGET_EXTS = { "py","js","ts","tsx","jsx","go","rs","java","kt","c","cpp","h","hpp","cs",
                                                    "yaml","yml","toml","json","ini","cfg","conf","md","mdx","rst","adoc",
                                                    "sh","zsh","bash","bat","ps1","ipynb" }
                                    EXCLUDE_DIRS = ("node_modules/","dist/","build/","venv/",".venv/","__pycache__/",".git/")
                                    SPECIAL = {"Dockerfile","docker-compose.yml","docker-compose.yaml","Makefile","CMakeLists.txt"}
                                    def _ok_path(p:str, size:int)->bool:
                                        if any(seg in p for seg in EXCLUDE_DIRS): return False
                                        if size and size>300_000: return False
                                        base = p.rsplit("/",1)[-1]
                                        if base in SPECIAL: return True
                                        if "." in base:
                                            ext = base.rsplit(".",1)[-1].lower()
                                            if ext in TARGET_EXTS and not base.endswith((".min.js",".bundle.js",".map")):
                                                return True
                                        return False
                                    candidates = []
                                    for it in items:
                                        u = it.get("url","")
                                        if "api.github.com/repos/" in u and "/git/trees/" in u:
                                            txt = it.get("raw") or it.get("text") or it.get("summary") or ""
                                            try:
                                                obj = json.loads(txt)
                                                for node in obj.get("tree", []):
                                                    if node.get("type") != "blob": 
                                                        continue
                                                    p = node.get("path","")
                                                    size = int(node.get("size") or 0)
                                                    if _ok_path(p, size):
                                                        candidates.append((p, size))
                                            except Exception:
                                                continue
                                    # 優先度：浅いパス優先 → 小さいサイズ優先
                                    candidates = sorted(set(candidates), key=lambda t: (t[0].count("/"), t[1] or 0))[:8]
                                    raw_urls = []
                                    if owner_repo and ref:
                                        raw_urls = [f"https://raw.githubusercontent.com/{owner_repo}/{ref}/{p}" for p,_ in candidates]
                                    # 3) raw を追加読取
                                    if raw_urls:
                                        # 認証ヘッダ（必要なら自動補完）
                                        extra_headers2 = getattr(action, "headers", None) if hasattr(action, "headers") else None
                                        if not extra_headers2:
                                            token = os.getenv("GITHUB_TOKEN")
                                            if token:
                                                extra_headers2 = {"Authorization": f"Bearer {token}"}
                                        items_raw = await read_urls(
                                            raw_urls,
                                            max_bytes = getattr(action, "max_bytes", 1_500_000) or 1_500_000,
                                            max_chars = getattr(action, "max_chars", 20_000) or 20_000,
                                            follow_pdfs = True,
                                            extract_images = True,
                                            analyze_images = False,
                                            language_hint = getattr(action, "language_hint", None),
                                            require_citations = True,
                                            headers = extra_headers2,
                                        )
                                        items.extend(items_raw)
                                        formatted = format_read_results_for_llm(items, require_citations=True)
                                        last_urls.extend([it.get("url") for it in items_raw if isinstance(it, dict) and it.get("url")])
                                        try:
                                            context_manager.set_meta(thread.id, "last_webread_urls", tuple(last_urls))
                                        except Exception:
                                            pass
                        except Exception as _e:
                            if printmsg or expmsg:
                                _print(f"[github raw follow-up skipped] {_e}", printmsg, expmsg)
                        # --- YAML駆動の抽出（summary上で簡易抽出） ---
                        extra_lines = []
                        intent_name = detect_intent(user_text, locale="ja")
                        if intent_name:
                            for i, it in enumerate(items, 1):
                                if "error" in it or it.get("is_pdf"):
                                    continue
                                text_for_extract = (it.get("summary") or "")
                                extra = extract_from_read(intent_name, it.get("url",""), text_for_extract, locale="ja")
                                if extra:
                                    extra_lines.append(f"{i}. {extra}")
                        # systemメッセージとして積む（\s プレフィックス）
                        result = f"\\sWEB読み取り結果:\n{formatted}"
                        if extra_lines:
                            result += "\n\n[抽出サマリ]\n" + "\n".join(extra_lines)
                except Exception as e:
                    result = f"web.read の実行中にエラーが発生しました: {e}"
                context_list.append(result)
                # 続行
                tool_runs += 1
                if tool_runs >= max_tool_steps:
                    if trace_tool:
                        chain = " → ".join(tool_trace + ["response(max-step)"])
                        print(f"[trace] {chain}")
                    break
                continue

            # 画像解析 ==========
            if action.tool == "web.image":
                try:
                    async with message.channel.typing():
                        provider = auth_data["chat"]["provider"]
                        model    = auth_data["vision"]["model"] if "vision" in auth_data else auth_data["chat"]["model"]
                        api_key  = auth_data["vision"]["api_key"] if "vision" in auth_data and auth_data["vision"].get("api_key") else auth_data["chat"]["api_key"]

                        # --- 重複起動ガード ---
                        user_last = ""
                        for m in reversed(context_list):
                            if isinstance(m, str) and not m.startswith("\\s"):
                                user_last = m
                                break
                        base_q = (user_last.strip() or "画像の内容を要約し、重要なポイントを箇条書きで説明してください。")

                        urls = list((action.image_urls or [])[:8])
                        sig = (tuple(urls), base_q)

                        # thread-scoped cache
                        last_sig = context_manager.get_meta(thread.id, "last_webimage_sig")
                        if last_sig == sig:
                            # 直近と同一 → 新規実行せず、続行（通常応答に任せる）
                            result = "\\s画像解析は直前の結果を再利用してください。"
                            context_list.append(result)
                            tool_runs += 1
                            continue
                        context_manager.set_meta(thread.id, "last_webimage_sig", sig)
                        # --- /重複起動ガード ---

                        # tasks に応じて軽く補足（describe/tags/ocr/nsfw_check）
                        extra = []
                        tset = set((getattr(action, "tasks", None) or []))
                        if "ocr" in tset:
                            extra.append("画像から読めるテキストを正確に抽出してください。")
                        if "tags" in tset:
                            extra.append("主要オブジェクトを3〜7語のタグで抽出してください。")
                        if "nsfw_check" in tset:
                            extra.append("成人向け/露出過多の可能性を簡潔に評価してください。")
                        # 言語ヒント
                        lang = getattr(action, "language_hint", None) or "ja"
                        extra.append("出力は" + ("日本語" if lang.startswith("ja") else "英語") + "で。")
                        question = base_q + ("\n" + "\n".join(extra) if extra else "")

                        # 実行
                        urls = list((action.image_urls or [])[:8])  # 上限8枚
                        if provider == "OpenAI":
                            vision_text = await analyze_openai_vision(urls, question, api_key, model)
                        elif provider == "Gemini":
                            vision_text = await analyze_gemini_vision(urls, question, api_key, model)
                        elif provider == "Claude":
                            vision_text = await analyze_claude_vision(urls, question, api_key, model)

                        # 次ターンの指針を明記（下のパッチ2とセット）
                        result = f"\\s画像解析の結果:\n{vision_text}\n\\s[web.image->chat] 次の1ターンはツールを起動せず、上の結果だけを根拠にユーザーの直近の問いに簡潔に答えてください。"
                        if printmsg or expmsg:
                            _print(f"webimage result => {vision_text[:2000]}", printmsg, expmsg)
                except Exception as e:
                    result = f"web.image の実行中にエラーが発生しました: {e}"
                context_list.append(result)
                # 続行
                tool_runs += 1
                if tool_runs >= max_tool_steps:
                    if trace_tool:
                        chain = " → ".join(tool_trace + ["response(max-step)"])
                        print(f"[trace] {chain}")
                    break
                continue

        # 不明なツール（将来拡張用） → 終了
        break

    # ===== 通常レスポンス送信 =====
    def _violates_repo_evidence(reply_text: str, last_read_urls: list[str]) -> bool:
        """
        GitHubレビュー用の簡易ガード:
        - 「ファイル別（最大8件）」の見出しがある
        - かつ raw.githubusercontent.com を読んだ URL 数 < 箇条書きの件数（ざっくり）
        → エビデンス不足とみなす
        """
        if not reply_text:
            return False
        # 対象セクション抽出：「ファイル別」〜「総評/根拠URL/末尾」
        start = reply_text.find("ファイル別")
        if start < 0:
            start = reply_text.find("ファイル別（最大8件）")
        if start < 0:
            return False
        end_candidates = [reply_text.find("総評", start), reply_text.find("根拠URL", start)]
        end_candidates = [p for p in end_candidates if p >= 0]
        end = min(end_candidates) if end_candidates else len(reply_text)
        section = reply_text[start:end]
        raw_count = sum(1 for u in (last_read_urls or []) if isinstance(u, str) and "raw.githubusercontent.com" in u)
        # セクション内の箇条書きのみカウント
        listed = sum(1 for line in section.splitlines() if line.lstrip().startswith(("-", "・")))
        if listed == 0:
            return False
        return raw_count < max(1, listed)
    if reply or pending_files:
        # オプション -printmsg:on, -expmsg:on 処理
        if printmsg or expmsg:
            _print(f"response => {(reply or '').strip()} [attachments={len(pending_files)}]", printmsg, expmsg)
        # モデルの癖で先頭に「 あいちゃぼ: 」が入った場合を除去
        if reply:
            reply = reply.replace("あいちゃぼ: ", "", 1)
        # 生のツールJSONを最終送信しない保険
        def _looks_like_tool_json(s: str) -> bool:
            try:
                import json
                obj = json.loads(s)
                return isinstance(obj, dict) and "tool" in obj
            except Exception:
                return False

        if (not pending_files) and reply and _looks_like_tool_json(reply):
            reply = "（内部処理が完了しませんでした。もう一度お試しください。）"
        # --- GitHubレビューの“根拠(=raw)必須”ガード ---
        try:
            intent_name_for_guard = detect_intent(user_text, locale="ja") or ""
            last_read_urls = context_manager.get_meta(thread.id, "last_webread_urls") or []
            if intent_name_for_guard == "github" and _violates_repo_evidence(reply or "", list(last_read_urls)):
                # 安全側に倒す：根拠不足の“ファイル別”は出力しない
                proof = [u for u in last_read_urls if "raw.githubusercontent.com" in (u or "")][:8]
                safe_msg = "対象拡張子のファイル本文（raw）が取得できていません。Tree/API の結果だけでは評価しません。\n" \
                           "もう一度お試しください。（必要に応じて『続き』と指示すると次の8件を読みます）\n" \
                           "根拠URL:\n" + "\n".join(f"  - {u}" for u in proof) if proof else \
                           "対象拡張子のファイル本文（raw）が取得できていません。Tree/API の結果だけでは評価しません。"
                reply = safe_msg
        except Exception:
            pass
        text_chunks = _split_for_discord(reply or "", limit=DISCORD_MSG_LIMIT)

        # 添付がある場合：1通目に本文(先頭チャンク)＋最初の添付群、以降は本文/添付を順次
        if pending_files:
            file_chunks = list(_chunks(pending_files, 10))
            # 1通目
            first_text = (text_chunks[0] if text_chunks else None) or None
            await message.channel.send(content=first_text, files=file_chunks[0])
            # 残りの本文
            for t in (text_chunks[1:] if text_chunks else []):
                await message.channel.send(t)
            # 残りの添付
            for fc in file_chunks[1:]:
                await message.channel.send(files=fc)
        else:
            # 添付なし：本文をチャンクごとに送信
            # 空文字は送らない
            if text_chunks:
                for t in text_chunks:
                    if t:
                        await message.channel.send(t)
            else:
                # 何も返すものが無ければ何もしない
                pass

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

    # メタ情報クリア
    try:
        context_manager.clear_meta(thread.id)
    except Exception:
        pass

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
    print(f"✅ {client.user} としてログインしました。")

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
        print("🔎 サーバー/スレッドの確認中...")
        existing_server_ids = {str(guild.id) for guild in client.guilds}
        thread_utils.clean_deleted_servers(SERVICE_NAME, existing_server_ids)

        # すべてのサーバー（Guild）に対して処理
        for guild in client.guilds:
            server_id = str(guild.id)
            thread_ids = set()

            # チャンネルごとの全スレッド
            for channel in guild.text_channels:
                # アクティブなスレッド
                for t in channel.threads:
                    thread_ids.add(str(t.id))

                # 公開アーカイブ
                try:
                    async for t in channel.archived_threads(limit=None):
                        thread_ids.add(str(t.id))
                except (discord.Forbidden, discord.HTTPException):
                    pass

                # 非公開アーカイブ（joined=True は「Botがメンバーの非公開スレ」）
                for joined in (True, False):
                    try:
                        async for t in channel.archived_threads(private=True, joined=joined, limit=None):
                            thread_ids.add(str(t.id))
                    except (discord.Forbidden, discord.HTTPException, AttributeError):
                        # 権限不足 or ライブラリ差異（古い版等）は握りつぶす
                        pass

            # スレッド存在チェック用に記憶されたスレッド一覧をクリーンアップ
            thread_utils.clean_deleted_threads(SERVICE_NAME, server_id, thread_ids)

        print("✅ 存在しないサーバー/スレッドのチェックおよびクリーンアップを完了しました")
        print("✅ 起動完了 (Ctrl-Cで終了します)")

    except Exception as e:
        print(f"❌ コマンド同期に失敗しました: {e}")
        await client.close()

# ===== Bot 起動 =====
def start_discord_bot():
    client.run(os.environ["DISCORD_BOT_TOKEN"])
