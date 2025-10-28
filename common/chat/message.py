# -*- coding: utf-8 -*-
"""
message.py（コメント付き完全版）
----------------------------------------------------------------------
役割：
- Discord 等のプラットフォーム固有層（events/）から渡される「受信メッセージ情報」
  を、チャット中核（chat_loop）へ橋渡しする“薄い”オーケストレータ。
- ここでは **APIキーを扱わない**・**プラットフォーム固有定数を持たない**
  （＝再利用性を高め、ユニットテストしやすくする）。

設計ポイント：
- message 層は「非機密（プロバイダ/モデルなどの“方針”）」のみ参照可。
  → 実キーの解決は chat_loop 側（common/chat/auth.resolve_auth_and_key()）で行う。
- Discord の「メッセージ長制限」等は **外部（呼び出し元の reply_fn）」に任せる**。
- “続きます／少々お待ちください”のような継続表現はここでサニタイズ可能
  （ただし再利用のため utility として分離）。

依存：
- common.session.server_session_manager（サーバー/スレッド方針・共用非機密）
- common.session.user_session_manager（ユーザー非機密）
- common.chat.chat_loop.run（コア推論ループ：ここで認証解決を実施）
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, List, Optional, Sequence, Tuple, Union
import asyncio
import time

# --- 内部依存（存在前提。パスはプロジェクト構成に合わせてください） ---
from common.session.server_session_manager import server_session_manager as SSM
from common.session.user_session_manager import user_session_manager as USM
from common.chat.provider import normalize_provider  # 参照のみ（厳密化に使う）
from common.utils.redact import redact  # 機密ぼかし（ログ用）
from common.chat import chat_loop  # 実本体：ここで鍵解決＋推論実行


# ========== 受け口：プラットフォーム非依存のメッセージ封筒 ==========
@dataclass
class MessageEnvelope:
    """
    送信元プラットフォームに依存しない“受信メッセージの封筒”。
    - Discord 側からは events/message.py 等で組み立て、handle_incoming_message() に渡す。
    - reply_fn は「**分割・長さ制限**を含む最終出力」を担当（＝ここでは気にしない）。
    """
    platform: str  # "discord" など
    guild_id: Optional[int]
    channel_id: Optional[int]
    thread_id: Optional[int]  # スレッド内会話のみ許可する方針などの判定に使う
    user_id: int
    user_name: str
    content: str
    attachments: Sequence[Dict[str, Any]]  # 画像/ファイル等（必要最小）
    is_dm: bool
    is_bot: bool
    created_ts: float

    # 返信を行うための非同期関数（**分割や装飾は呼び出し側で実施**）
    reply_fn: Callable[[str], Awaitable[None]]

    # typing表示などのオプションコールバック（任意）
    typing_on: Optional[Callable[[], Awaitable[None]]] = None
    typing_off: Optional[Callable[[], Awaitable[None]]] = None

    # 追加メタ（プラットフォーム固有情報を透過したい場合に拡張）
    meta: Dict[str, Any] = None


# ========== サニタイズ：継続表現の調整（共通ユーティリティ） ==========
_CONTINUATION_PATTERNS = (
    "すぐに続けますね", "少々お待ちください", "続けますか？", "続きを書きます", "続きます", "続けます", "もう少しだけお待ちください",
)

def sanitize_continuation_phrases(text: str) -> str:
    """
    “待って/続ける”系の表現を、ユーザーの操作誘導・誤期待を避ける文にシフト。
    - ※ 本文全除去までは行わず、「ここで完結させる」トーンへ寄せる。
    - プロジェクト方針に応じて完全削除したい場合はこの関数を差し替え。
    """
    t = text
    for p in _CONTINUATION_PATTERNS:
        if p in t:
            # ここでは穏当な言い換えにとどめる
            t = t.replace(p, "このメッセージで完結します")
    return t


# ========== コンテキスト構築（非機密のみ） ==========
def build_context(envelope: MessageEnvelope) -> Dict[str, Any]:
    """
    チャット実行用の“非機密”コンテキストを組み立てる。
    - USM(ユーザー設定) を優先、無ければ SSM(サーバー共有設定) を参照
    - ここでは **APIキーは扱わない**（= chat_loop 側で resolve する）
    - Discord の “スレッド限定” 方針などは **SSMのオプション**から読む。
    """
    guild_id = envelope.guild_id
    user_id = envelope.user_id

    # サーバー/スレッド運用オプション（printmsg, expmsg, threads_only など）
    server_opts = dict(SSM.all_options(guild_id)) if guild_id else {}
    threads_only = bool(server_opts.get("threads_only", True))  # 既定: スレッド内のみ許可

    # 受信メッセージがスレッド外なら、方針に従い“誘導用フラグ”を立てて返す
    thread_policy_violation = False
    if threads_only and not envelope.thread_id and not envelope.is_dm:
        thread_policy_violation = True

    # ユーザー非機密（優先）
    user_auth = USM.get_session(user_id) or {}
    # サーバー共有非機密（ユーザー未設定時のフォールバック）
    server_shared = SSM.get_shared_auth_config(guild_id) if guild_id else {}

    # 採用Auth（非機密）を合成：ユーザー優先 → 無ければサーバー共有 → それでも無ければ空
    def _pick(section: str) -> Dict[str, Any]:
        u = (user_auth.get(section) or {})
        if u.get("provider") and u.get("model"):
            return {"provider": normalize_provider(u["provider"]), "model": u["model"], **{k:v for k,v in u.items() if k not in ("provider","model")}}
        s = (server_shared.get(section) or {})
        if s.get("provider") and s.get("model"):
            return {"provider": normalize_provider(s["provider"]), "model": s["model"], **{k:v for k,v in s.items() if k not in ("provider","model")}}
        return {}

    non_secret_auth = {
        "chat":    _pick("chat"),
        "vision":  _pick("vision"),
        "imagegen":_pick("imagegen"),
    }

    ctx = {
        "platform": envelope.platform,
        "guild_id": guild_id,
        "channel_id": envelope.channel_id,
        "thread_id": envelope.thread_id,
        "user_id": user_id,
        "user_name": envelope.user_name,
        "created_ts": envelope.created_ts,
        "options": server_opts,
        "non_secret_auth": non_secret_auth,  # ← 鍵は無し（chat_loop で解決）
        "attachments": list(envelope.attachments or []),
        "thread_policy_violation": thread_policy_violation,
        # 必要に応じて将来的に system_prompts の選択などをここで行う
    }
    return ctx


# ========== 入口：受信メッセージの処理 ==========
async def handle_incoming_message(envelope: MessageEnvelope) -> None:
    """
    プラットフォーム層（Discordの on_message 等）から呼ばれる入口。
    - ここでは「軽い前処理」を行い、chat_loop へ委譲する。
    - 返信は **envelope.reply_fn** を通して行う（=分割・制限は呼び出し側の責務）。
    """
    # 1) Bot/自分自身メッセージ等はスルー（上位層で弾いていれば冗長）
    if envelope.is_bot:
        return
    if not envelope.content and not envelope.attachments:
        # 何もない場合は終了（必要なら「空メッセージです」など案内）
        return

    # 2) スレッド運用方針等の判定も含めてコンテキストを構築（非機密のみ）
    ctx = build_context(envelope)

    # 3) スレッド外禁止の場合のガイド（ここで軽くガード）
    if ctx.get("thread_policy_violation"):
        # ガイドは短く・具体的に（Discord 側で /ac_invite を案内）
        await envelope.reply_fn(
            "このチャンネルではスレッド内のみ会話できます。必要なら `/ac_invite` で招待してから、このメッセージでスレッドを作成して続けてください。"
        )
        return

    # 4) 継続表現のサニタイズ（“待ち”を期待させない）
    user_text = sanitize_continuation_phrases(envelope.content)

    # 5) 可能なら typing 表示（非同期：失敗しても無視）
    typing_task = None
    if envelope.typing_on is not None:
        try:
            await envelope.typing_on()
        except Exception:
            pass

    # 6) 推論本体（鍵解決含む）は chat_loop に委譲
    #    - chat_loop 側は resolve_auth_and_key() を内部利用
    #    - 返却は “最終テキスト” か “複合（テキスト＋画像/タスク）”など、将来的に拡張可能
    try:
        result = await chat_loop.run(
            user_text=user_text,
            context=ctx,
        )
    except Exception as e:
        # 失敗時は最小の案内（詳細はログへ）。機密を含む値は redact。
        await envelope.reply_fn("処理中にエラーが発生しました。設定や認証情報（/ac_status, /ac_auth）をご確認ください。")
        # ここでログに残す（機密ぼかし）
        try:
            from common.utils.logger import log_error  # 任意のロガー（存在すれば）
            log_error(f"[message] chat_loop failed: {redact(str(e))}")
        except Exception:
            pass
        return
    finally:
        # typing off
        if envelope.typing_off is not None:
            try:
                await envelope.typing_off()
            except Exception:
                pass

    # 7) 出力の整形と返信
    #    - “message 層”はテキストをそのまま返す（分割や embed は reply_fn 側の責務）
    #    - result が dict/複合の可能性を考慮（将来拡張）
    if isinstance(result, str):
        out_text = result
    elif isinstance(result, dict) and "text" in result:
        out_text = str(result.get("text") or "")
    else:
        # 型不一致のフォールバック
        out_text = str(result)

    out_text = sanitize_continuation_phrases(out_text).strip()
    if not out_text:
        out_text = "（応答が空でした）"

    await envelope.reply_fn(out_text)


# ========== 参考：最小の reply_fn 実装例（テスト用） ==========
async def _console_reply_fn_for_tests(text: str) -> None:
    """
    ユニットテストや utiltests で使う簡易返信関数。
    - Discord の長さ制限等は行わず、そのまま標準出力へ出す。
    """
    print(text)


# ========== 参考：utiltests からの呼び出しスケルトン ==========
async def run_once_for_test(
    user_text: str,
    user_id: int = 111,
    guild_id: Optional[int] = 222,
    thread_id: Optional[int] = 333,
) -> None:
    """
    utiltests から直接 message 層を叩きたい時の最小スケルトン。
    - Discord を通さずに message → chat_loop の流れだけ検証できる。
    """
    env = MessageEnvelope(
        platform="test",
        guild_id=guild_id,
        channel_id=None,
        thread_id=thread_id,
        user_id=user_id,
        user_name="Tester",
        content=user_text,
        attachments=[],
        is_dm=False,
        is_bot=False,
        created_ts=time.time(),
        reply_fn=_console_reply_fn_for_tests,
        typing_on=None,
        typing_off=None,
        meta={}
    )
    await handle_incoming_message(env)
