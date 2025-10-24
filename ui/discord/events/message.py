# ui/discord/events/message.py
# on_message を“薄い”まま保ちつつ、build_context() で
# - 認証情報（/ac_auth で登録済みのもの）
# - プラグイン system プロンプト（あれば）
# をまとめて返す。

import discord
from ..runtime.client import client
from ..render.formatting import send_reply
from ..utils.log import _print

# 追加：認証・オプションの取得（既存のセッション管理を流用）
# - モジュール名/関数名はあなたの実装に合わせてあります（過去ログ準拠）
from common.session.server_session_manager import server_session_manager as ssm  # 既存の取得口
from common.plugins.dispatcher import list_providers  # 表示のみ（任意）
# プラグインの system プロンプトは dispatcher 側で meta に積む想定。
# build_context() では「ユーザー設定のsystemや、全体system」などを合流しておく。

async def build_context(message: discord.Message) -> dict:
    """
    既存の文脈構築をここに集約：
      - guild_id / user_id から /ac_auth の認証を取得
      - 必要なら /ac_status のオプションも読む
      - system_msgs は、今は空リスト（プラグイン命中時に services 側で追記する）
    """
    guild_id = getattr(message.guild, "id", None)
    user_id = getattr(message.author, "id", None)

    # 1) 認証（/ac_auth の登録内容）を取得
    #    例：{"chat":{"provider":"OpenAI","api_key":"...","model":"gpt-4o-mini", ...}, ...}
    auth = ssm.get_auth(guild_id=guild_id, user_id=user_id)  # あなたの実装の戻り形に合わせてください
    if not auth or "chat" not in auth:
        # 最低限のダミー。実際には /ac_auth を案内
        auth = {"chat": {"provider": "OpenAI", "api_key": "", "model": "gpt-4o-mini", "max_tokens": 1024}}

    # 2) オプション（printmsg など）を読む（任意）
    options = {
        "printmsg": ssm.get_option(guild_id, "printmsg", False) if guild_id else False,
        "expmsg": ssm.get_option(guild_id, "expmsg", False) if guild_id else False,
    }

    # 3) system メッセージ（全体/ユーザー/プラグイン用）— まずは空で返す
    system_msgs: list[str] = []

    return {
        "guild_id": guild_id,
        "user_id": user_id,
        "auth": auth,
        "options": options,
        "system_msgs": system_msgs,  # プラグイン命中時に services/chat_loop 側で先頭に注入
    }

@client.event
async def on_message(message: discord.Message):
    """通常チャットのエントリ。services 層へ委譲するだけ。"""
    if message.author.bot:
        return
    from ..services import chat_loop  # 循環回避のため遅延 import
    ctx = await build_context(message)
    reply, files = await chat_loop.run(message, ctx, prefetch=None)
    await send_reply(message.channel, reply, files)
