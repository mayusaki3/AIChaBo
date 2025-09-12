from __future__ import annotations

import mimetypes
from collections import defaultdict
from typing import Any, Dict, List, Optional

import discord
from common.session.thread_context_manager import ThreadContextManager

# コンテキスト情報として、以下の内容を保持する。
# - 収集範囲 : スレッド内の開始位置以降のすべてのメッセージ
# - 開始位置 : 以下の条件のうち、一番後の位置（ui毎のthread_context内で判定）
#              1. 先頭メッセージ
#              2. /ac_summary の結果メッセージ
#              3. /ac_newtopic の次のメッセージ
# - 保持内容 : { "message": 発言者: メッセージ内容,
#                ※ 以下で始まるメッセージは無視
#                  ⚠️ 認証情報を
#                  💬/ac_newchat:
#                  💬/ac_invite:
#                  💬/ac_leave:
#                "msgid": メッセージID,
#                "refid": 返信元メッセージID,
#                "attachments": メッセージの添付（UI依存の構造を許容）,
#                "state": "OK"=完了 / ""=未処理・処理中（値はUI依存で拡張可） }
class DiscordThreadContextManager:
    # 無視すべきメッセージの接頭語
    SKIP_PREFIXES = (
        "⚠️ あいちゃぼと会話するには、", "⚠️ 認証情報を", "💬/ac_newchat:", "💬/ac_invite:", "💬/ac_leave:"
    )

    # あいちゃぼのユーザー名
    AICHABO_NAMES= (
        "AIChatBot:", "AIChatBot Dev:", "あいちゃぼ:", "あいちゃぼ Dev:"
    )

    def __init__(self) -> None:
        self.manager = ThreadContextManager()
        self.initialized_threads: set[str] = set()
        self._thread_meta: dict[str, dict[str, Any]] = defaultdict(dict)

    # --- メタ情報API ---
    def get_meta(self, thread_id: str | int, key: str, default=None):
        return self._thread_meta.get(str(thread_id), {}).get(key, default)

    def set_meta(self, thread_id: str | int, key: str, value: Any) -> None:
        tid = str(thread_id)
        if tid not in self._thread_meta:
            self._thread_meta[tid] = {}
        self._thread_meta[tid][key] = value

    def pop_meta(self, thread_id: str | int, key: str, default=None):
        return self._thread_meta.get(str(thread_id), {}).pop(key, default)

    def clear_meta(self, thread_id: str | int) -> None:
        self._thread_meta.pop(str(thread_id), None)

    # スレッドIDごとに未初期化ならコンテキスト履歴を再構築
    async def ensure_initialized(self, thread: discord.Thread) -> None:
        thread_id = str(thread.id)
        if thread_id in self.initialized_threads:
            return
        await self.load_context_from_history(thread)

    # スレッドIDごとにスレッド履歴からコンテキスト履歴を再構築
    async def load_context_from_history(self, thread: discord.Thread) -> None:
        # print(f"L [START]: {thread.name}")
        thread_id = str(thread.id)
        self.clear_context(thread_id)

        messages: List[discord.Message] = []
        async for msg in thread.history(limit=100, oldest_first=False):
            if msg.author.bot:
                # 無視すべきBotメッセージか
                if any(msg.content.startswith(p) for p in self.SKIP_PREFIXES):
                    # print(f"  [SKIP ]: {msg.content}")
                    continue
                # 要約が見つかったら3行目以降の内容を取り込み処理終了
                if msg.content.startswith("💬/ac_summary:"):
                    lines = msg.content.splitlines()
                    if len(lines) > 2:
                        msg.content = "\n".join(lines[2:])  # 3行目以降のみ使用
                        # print(f"  [要約 ]: {msg.content}")
                        messages.append(msg)
                    break
                # 新規トピックが見つかったら打ち切り
                if msg.content.startswith("💬/ac_newtopic:"):
                    break
            # print(f"  [MSG  ]: {msg.content}")
            messages.append(msg)

        # 古い→新しい順に格納
        for msg in reversed(messages):
            author_name = msg.author.name
            refid = str(msg.reference.message_id) if (msg.reference and msg.reference.message_id) else ""
            atts = self._normalize_image_attachments(msg.attachments)
            entry = self.append_context(
                thread_id=str(thread.id),
                message=f"{author_name}: {msg.content}",
                msgid=str(msg.id),
                refid=refid,
                attachments=atts if atts else None,
            )
            # if entry is not None:
            #     print(f"  [MSG++]: {entry['message']}")

        # print(f"L [END  ]: {thread.name}")

    # メッセージ重複チェック: すでに同じ msgid が格納済みかを確認
    def _has_msg(self, thread_id: str, msgid: str) -> bool:
        tid = str(thread_id)
        mid = str(msgid)
        return any(e.get("msgid") == mid for e in self.manager.get_context(tid))

    # 現メッセージの返信履歴を取り込む
    async def backfill_reply_chain(
        self,
        thread: discord.Thread,
        leaf_msg: discord.Message,
        max_hops: int = 10,
    ) -> int:
        # 返信チェーンを親方向へたどり、未格納メッセージを古→新の順で追加する
        thread_id = str(thread.id)
        added = 0
        chain: list[discord.Message] = []
        seen: set[int] = set()

        cur = leaf_msg
        while (
            cur.reference
            and cur.reference.message_id
            and len(chain) < max_hops
        ):
            parent_id = int(cur.reference.message_id)
            if parent_id in seen:
                break
            seen.add(parent_id)

            try:
                parent = await thread.fetch_message(parent_id)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                break

            chain.append(parent)
            cur = parent

        # 親→子の順（古い→新しい）で追加
        for m in reversed(chain):
            if self._has_msg(thread_id, m.id):
                continue
            author_name = m.author.display_name
            refid = (
                str(m.reference.message_id)
                if (m.reference and m.reference.message_id)
                else ""
            )
            atts = self._normalize_image_attachments(m.attachments)
            entry = self.append_context(
                thread_id=thread_id,
                message=f"{author_name}: {m.content}",
                msgid=str(m.id),
                refid=refid,
                attachments=atts if atts else None,
            )
            if entry is not None:
                added += 1

        return added

    # message が返信であれば、返信元を最大 max_hops 回たどって返す
    async def fetch_parent_chain(
        self,
        thread: discord.Thread,
        message: discord.Message,
        max_hops: int = 5
    ) -> List[discord.Message]:
        chain = []
        cur = message
        hops = 0

        while getattr(cur, "reference", None) and getattr(cur.reference, "message_id", None):
            if hops >= max_hops:
                break
            try:
                parent = await thread.fetch_message(cur.reference.message_id)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                break
            chain.append(parent)
            cur = parent
            hops += 1

        chain.reverse()
        return chain

    # messageからメッセージ本文を取得
    def _raw_text(self, message: str) -> str:
        # '名前: 本文' 形式なら本文だけを取り出して判定に使う
        parts = message.split(":", 1)
        return parts[1].lstrip() if len(parts) == 2 else message

    # スレッドIDごとにメッセージを追加
    def append_context(
        self,
        thread_id: str,
        message: str,
        msgid: str,
        refid: str | None,
        attachments: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[Dict[str, Any]]:
        msg = message
        raw = self._raw_text(msg)
        if any(raw.startswith(p) for p in self.SKIP_PREFIXES):
            return None
        if any(msg.startswith(p) for p in self.AICHABO_NAMES):
            msg = f"あいちゃぼ: {raw}"
        return self.manager.append_context(thread_id, msg, msgid, refid, attachments)

    # スレッドIDごとにコンテキストを取得
    def get_context(self, thread_id: str) -> List[Dict[str, Any]]:
        return self.manager.get_context(thread_id)

    # 追加情報注入用メッセージを取得
    def get_injection_message(self, auth_data: dict) -> str:
        return self.manager.get_injection_message(auth_data)

    # スレッドIDごとにコンテキストをクリア
    def clear_context(self, thread_id: str) -> None:
        thread_id = str(thread_id)
        if thread_id not in self.initialized_threads:
            self.initialized_threads.add(thread_id)
            # print(f"- [INIT ]: {thread_id}")
        self.manager.clear_context(thread_id)
        self.clear_meta(thread_id)

    # スレッドIDごとにコンテキストをリセット
    def reset_context(self, thread_id: str) -> None:
        thread_id = str(thread_id)
        if thread_id in self.initialized_threads:
            self.initialized_threads.remove(thread_id)
            print(f"- [RESET]: {thread_id}")
        self.manager.clear_context(thread_id)
        self.clear_meta(thread_id)

    # スレッドIDが初期化されているか確認
    def is_initialized(self, thread_id: str) -> bool:
        return str(thread_id) in self.initialized_threads

    # 指定したスレッドのコンテキストをエクスポート
    def export_context(self, thread_id: str) -> str:
        return self.manager.export_context(str(thread_id))

    # 全スレッドをエクスポート
    def export_all_contexts(self) -> List[str]:
        return self.manager.export_all()

    # Vision AI用に添付画像を抽出し dict に格納
    def _normalize_image_attachments(
        self, attachments: List[discord.Attachment]
    ) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for att in attachments:
            ct = (att.content_type or "").lower()
            if not ct:
                guess, _ = mimetypes.guess_type(att.filename)
                ct = (guess or "").lower()

            is_image = ct.startswith("image/")
            # 拡張子でも判断
            if not is_image:
                is_image = any(att.filename.lower().endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".webp", ".gif"))

            if not is_image:
                continue

            out.append({
                "type": "image",
                "url": att.url,                # Vision API に渡せる CDN URL
                "proxy_url": att.proxy_url,    # Discord 側のプロキシ URL
                "content_type": ct or None,
                "filename": att.filename,
                "size": att.size,
                "width": getattr(att, "width", None),
                "height": getattr(att, "height", None),
                # 後で埋めるタグ情報
                "has_reply_tag": False,
                "reply_message_ids": [],
            })
        return out


# シングルトンとして使うインスタンス
context_manager = DiscordThreadContextManager()