# -*- coding: utf-8 -*-
"""
ui/discord/events/message.py
----------------------------------------------------------------------
Discord固有の on_message リスナ。
- 受信メッセージをプラットフォーム非依存の「封筒（MessageEnvelope）」に詰め替え、
  common側の message.handle_incoming_message() に委譲する。
- Discord固有の長文分割（2000文字制限）もここで実施。
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

import discord
from ui.discord.runtime.client import client  # 既存の client シングルトン
from common.utils.redact import redact

# 共通の薄いオーケストレータ（鍵は扱わない・LLM呼び出しは chat_loop 側）
from common.chat.message import MessageEnvelope, handle_incoming_message


# --- Discord固有：長文分割（ここでのみ2000文字を意識する） ----------------
DISCORD_MSG_LIMIT = 2000

async def _discord_reply_split(channel: discord.abc.Messageable, text: str) -> None:
    """2000字制限に合わせて分割送信する。Embed等はここでは使わない。"""
    if not text:
        return
    chunks: List[str] = []
    t = text
    while len(t) > DISCORD_MSG_LIMIT:
        chunks.append(t[:DISCORD_MSG_LIMIT])
        t = t[DISCORD_MSG_LIMIT:]
    chunks.append(t)
    for part in chunks:
        await channel.send(part)


# --- Discord固有：typingインジケーター -------------------------------------
class _TypingSpinner:
    """背景で一定間隔 typing を点灯させ続け、stop で終了する。"""
    def __init__(self, channel: discord.abc.Messageable):
        self._channel = channel
        self._stop = asyncio.Event()
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._task = asyncio.create_task(self._runner())

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            try:
                await self._task
            except Exception:
                pass

    async def _runner(self) -> None:
        # discord.py は typing() をコンテキスト化すると数秒表示される。
        # これを一定間隔で繰り返す。
        try:
            while not self._stop.is_set():
                async with self._channel.typing():
                    await asyncio.sleep(8)  # 体感持続時間に合わせて適度にスリープ
        except Exception:
            # typing失敗は無視（権限等の問題を想定）
            return


# --- Discord -> 共通層 変換 -------------------------------------------------
def _to_envelope(msg: discord.Message) -> MessageEnvelope:
    guild_id = msg.guild.id if msg.guild else None
    channel_id = msg.channel.id if msg.channel else None
    thread_id: Optional[int] = None
    # スレッドなら thread_id を持たせる
    if isinstance(msg.channel, discord.Thread):
        thread_id = msg.channel.id

    # 添付ファイルの最小情報を抽出（後段で必要になれば拡張）
    atts: List[Dict[str, Any]] = []
    for a in msg.attachments:
        atts.append({
            "filename": a.filename,
            "content_type": a.content_type,
            "size": a.size,
            "url": a.url,
            "proxy_url": a.proxy_url,
            "height": getattr(a, "height", None),
            "width": getattr(a, "width", None),
        })

    # typingインジケータ制御
    spinner = _TypingSpinner(msg.channel)

    async def _typing_on():
        await spinner.start()

    async def _typing_off():
        await spinner.stop()

    async def _reply_fn(text: str):
        await _discord_reply_split(msg.channel, text)

    env = MessageEnvelope(
        platform="discord",
        guild_id=guild_id,
        channel_id=channel_id,
        thread_id=thread_id,
        user_id=msg.author.id,
        user_name=getattr(msg.author, "display_name", str(msg.author)),
        content=msg.content or "",
        attachments=atts,
        is_dm=(msg.guild is None),
        is_bot=getattr(msg.author, "bot", False),
        created_ts=msg.created_at.timestamp() if msg.created_at else 0.0,
        reply_fn=_reply_fn,
        typing_on=_typing_on,
        typing_off=_typing_off,
        meta={
            "message_id": msg.id,
            "author": str(msg.author),
        },
    )
    return env


# --- on_message リスナ ------------------------------------------------------
@client.event
async def on_message(msg: discord.Message):
    """Discordのメッセージ受信イベント。Bot/自己発言は弾き、共通層へ委譲。"""
    try:
        # Bot/自分はスキップ
        if getattr(msg.author, "bot", False):
            return
        # スラッシュコマンドは app_commands 側で処理されるためここでは無視
        if msg.content.startswith("/"):
            return

        env = _to_envelope(msg)
        await handle_incoming_message(env)

    except Exception as e:
        # 最低限のログのみ（機密は redact）
        try:
            from common.utils.logger import log_error
            log_error(f"[on_message] failed: {redact(str(e))}")
        except Exception:
            pass
