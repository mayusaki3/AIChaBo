# ui/discord/events/message.py
# ------------------------------------------------------------
# on_message: “薄い”イベント。build_context() で非機密設定だけ解決。
# - auth: USM（ユーザー）→なければ SSM（共有）でフォールバック
# - 鍵は LLM 呼出直前に SecretStore から取得（ここでは扱わない）
# ------------------------------------------------------------
import discord
from ..runtime.client import client
from ..render.formatting import send_reply
from ..utils.log import _print

from common.session.user_session_manager import user_session_manager as USM
from common.session.server_session_manager import server_session_manager as SSM
from common.plugins.dispatcher import list_providers  # 将来の可視化用

async def build_context(message: discord.Message) -> dict:
    guild_id = getattr(message.guild, "id", None)
    user_id  = getattr(message.author, "id", None)

    # 1) 非機密設定の解決（ユーザー優先 → サーバー共有）
    auth = USM.get_session(user_id) or SSM.get_shared_auth_config(guild_id) or {}
    if not auth or "chat" not in auth:
        # 実運用では /ac_auth を案内。ここでは空を返す。
        auth = {"chat": {"provider": "", "model": ""}}

    # 2) オプション（必要なら）
    options = {
        "printmsg": SSM.get_option(guild_id, "printmsg", False) if guild_id else False,
        "expmsg":   SSM.get_option(guild_id, "expmsg",   False) if guild_id else False,
    }

    system_msgs: list[str] = []

    return {
        "guild_id": guild_id,
        "user_id": user_id,
        "auth": auth,          # 非機密のみ。api_keyは含まない
        "options": options,
        "system_msgs": system_msgs,
    }

@client.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    from ..services import chat_loop  # 循環回避
    ctx = await build_context(message)
    reply, files = await chat_loop.run(message, ctx, prefetch=None)
    await send_reply(message.channel, reply, files)
