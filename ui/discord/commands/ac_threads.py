# ui/discord/commands/ac_threads.py
# ------------------------------------------------------------
# /ac_threads: あいちゃぼと会話中のスレッド一覧を表示
# - コマンドを実行したユーザーが参加していないプライベートスレッドは
#   スレッド名を「？？？？？」で表示
# ------------------------------------------------------------
import discord
from discord import app_commands, Interaction, Thread, ChannelType, Forbidden, HTTPException
from common.utils.thread_utils import load_server_threads

HELP_TEXT = {
    "usage": "/ac_threads [option]",
    "description": "あいちゃぼと会話中のスレッド一覧を表示します。\n"
                   "option: serverlist / channellist / all"
}

SERVICE_NAME = "discord"

def get_command():
    return app_commands.Command(
        name="ac_threads",
        description=HELP_TEXT["description"],
        callback=ac_threads_command,
    )

@app_commands.describe(option="serverlist / channellist / all")
async def ac_threads_command(interaction: Interaction, option: str | None = None):
    await interaction.response.defer(thinking=True, ephemeral=True)
    client = interaction.client

    # --- オプション解析（複数指定時の優先順位: all > channellist > serverlist） ---
    optset = set()
    if option:
        optset = {t.strip().lower() for t in option.split() if t.strip()}
    if "all" in optset:
        mode = "all"
    elif "channellist" in optset:
        mode = "channellist"
    elif "serverlist" in optset:
        mode = "serverlist"
    else:
        mode = "current"  # 既定：現在サーバーのみ

    # 収集対象サーバー
    if mode == "current":
        guilds = [interaction.guild] if interaction.guild else []
    else:
        guilds = list(getattr(client, "guilds", []) or [])

    # 構造: servers[guild_id] = {"name": guild_name, "channels": { (chan_name, chan_id): [ (thr_name, thr_id, hidden) ] } }
    servers: dict[int, dict] = {}
    for g in guilds:
        thread_ids = load_server_threads(SERVICE_NAME, g.id) or []
        if not thread_ids:
            continue
        gentry = servers.setdefault(g.id, {"name": g.name, "channels": {}})
        for tid in thread_ids:
            try:
                t = await g.fetch_channel(tid)
                if not isinstance(t, Thread):
                    continue
                is_private = t.type == ChannelType.private_thread
                # 実行者がスレッドメンバーか
                user_is_member = False
                try:
                    await t.fetch_member(interaction.user.id)
                    user_is_member = True
                except (Forbidden, HTTPException):
                    user_is_member = False
                # 親チャンネル
                parent = None
                try:
                    parent = t.parent or g.get_channel(getattr(t, "parent_id", None)) or None
                except Exception:
                    parent = None
                chan_name = (parent.name if parent else "？？？？？") if (not is_private or user_is_member) else "？？？？？"
                chan_id   = getattr(t, "parent_id", None) or (parent.id if parent else "不明")
                thr_name  = (t.name if (not is_private or user_is_member) else "？？？？？")
                key = (chan_name, chan_id)
                gentry["channels"].setdefault(key, []).append((thr_name, t.id))
            except Exception:
                # 取得失敗は無視（整形を崩さない）
                continue

    # 何もなければ終了
    if not servers:
        await interaction.followup.send("📭 会話中のスレッドはありません。", ephemeral=True)
        return

    # ソート: サーバー名 → チャンネル名 → スレッド名（名前でソート）
    def _key(s: str) -> str:
        try: return s.casefold()
        except Exception: return s

    # 見出しを mode で切替
    if mode == "serverlist":
        header = "🧵 会話中のサーバー一覧"
    elif mode == "channellist":
        header = "🧵 会話中のチャンネル一覧"
    else:
        header = "🧵 会話中のスレッド一覧"
    lines: list[str] = [header]
    for gid, sdata in sorted(servers.items(), key=lambda kv: _key(kv[1]["name"])):
        # serverlist：サーバー名＋ギルドID
        if mode == "serverlist":
            lines.append(f"{sdata['name']}\t（ID: {gid}）")
            continue

        lines.append(f"{sdata['name']}\t（ID: {gid}）")
        # channellist：サーバー名＋チャンネル名のみ
        if mode == "channellist":
            for (cname, cid), _threads in sorted(sdata["channels"].items(), key=lambda kv: _key(kv[0][0])):
                lines.append(f"＃ {cname}\t（ID: {cid}）")
            continue

        # all / current：フル表示（サーバー→チャンネル→スレッド）
        for (cname, cid), threads in sorted(sdata["channels"].items(), key=lambda kv: _key(kv[0][0])):
            lines.append(f"＃ {cname}\t（ID: {cid}）")
            for thr_name, thr_id in sorted(threads, key=lambda x: _key(x[0])):
                lines.append(f"　 -  {thr_name}\t（ID: {thr_id}）")

    await interaction.followup.send("\n".join(lines), ephemeral=True)
