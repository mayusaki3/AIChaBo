# -*- coding: utf-8 -*-
# common/chat/continuation.py
"""
Continuation flow for multi-step chat.

要点:
- messages を正規化（message.normalize_messages / join_messages）
- 連結 → textsplit.split_text で分割 → chat_loop.chat を逐次呼び出し
- max_steps<=0 / 空チャンク / textsplit 例外時は chat_loop を呼ばない
- 例外は握り潰して空文字を返す（テスト「例外握り潰し」準拠）
- テスト都合（self.cont(...) で呼ばれる）に合わせ、先頭の余分な位置引数(self)を吸収する
- モジュール属性: chat_loop / message / textsplit を公開（patch 対象）

公開API:
    continue_chat(messages, policy=None, *, max_steps=...) -> str
"""
from __future__ import annotations
from typing import Any, Dict, List, Tuple, Iterable, Union, Optional

# --- テストで patch 可能にするためモジュール属性として公開 ---
from . import chat_loop as chat_loop       # noqa: F401
from . import message as message           # noqa: F401
from . import textsplit as textsplit       # noqa: F401

__all__ = ["continue_chat"]

MessageLike = Union[str, Dict[str, Any]]
MessagesInput = Union[MessageLike, Iterable[MessageLike]]


# --------------------------
# 引数互換: self バインド吸収
# --------------------------
def _unpack_args_kwargs(args: Tuple, kwargs: dict) -> Tuple[MessagesInput, Optional[Dict[str, Any]], Dict[str, Any]]:
    """
    self.cont(messages=..., policy=..., max_steps=...) / continue_chat(msgs, policy)
    の両呼び出し形を許容するための互換レイヤ。
    """
    # 先頭に self が来る場合を吸収（list/str/dict 以外なら self とみなす）
    if args and not isinstance(args[0], (list, str, dict)):
        args = args[1:]

    # messages
    if "messages" in kwargs:
        messages = kwargs.pop("messages")
    elif args:
        messages = args[0]
        args = args[1:]
    else:
        messages = []

    # policy
    if "policy" in kwargs:
        policy = kwargs.pop("policy")
    elif args:
        policy = args[0]
        args = args[1:]
    else:
        policy = None

    # 残余は extra（chat_loop.chat へ透過）
    extra = dict(kwargs)

    return messages, policy, extra


# --------------------------
# 正規化ユーティリティ
# --------------------------
def _normalize_messages(messages_in: MessagesInput) -> List[Dict[str, Any]]:
    """
    message.normalize_messages があればそれを利用。なければ最小限で整形。
    - str -> [{'role':'user','content':text}]
    - dict 単体 -> [dict]
    - Iterable[str|dict] -> 上記の配列
    """
    norm = getattr(message, "normalize_messages", None)
    if callable(norm):
        return norm(messages_in)

    # フォールバック（最小実装）
    if isinstance(messages_in, str):
        return [{"role": "user", "content": messages_in}]
    if isinstance(messages_in, dict):
        return [messages_in]
    if isinstance(messages_in, Iterable):
        out: List[Dict[str, Any]] = []
        for m in messages_in:
            if isinstance(m, str):
                out.append({"role": "user", "content": m})
            elif isinstance(m, dict):
                out.append(m)
            else:
                raise TypeError("messages iterable must contain str or dict")
        return out
    raise TypeError("messages must be str/dict or iterable thereof")


def _join_contents(msgs: List[Dict[str, Any]]) -> str:
    """
    content を順に連結。message.join_messages があれば利用。
    """
    joiner = getattr(message, "join_messages", None)
    contents = [m.get("content") for m in msgs if isinstance(m, dict)]
    contents = [c for c in contents if isinstance(c, str)]
    if callable(joiner):
        return joiner(contents)
    # フォールバック: 単純結合（必要最低限）
    return "".join(contents)


# --------------------------
# 本体
# --------------------------
def continue_chat(*args, **kwargs) -> str:
    """
    会話継続のメイン入口。
    - 正規化 → 連結 → 分割 → chat_loop.chat を順次呼び出し
    - 例外/境界条件では安全に早期終了
    :param messages: str/dict/それらの反復（self バインド吸収対応）
    :param policy: provider/model 等（任意）
    :return: 最終応答（None の場合は ""）
    """
    try:
        messages_in, policy, extra = _unpack_args_kwargs(args, kwargs)
    except Exception:
        return ""

    # policy が None でも落ちない
    p: Dict[str, Any] = policy if isinstance(policy, dict) else {}

    # ステップ上限
    try:
        max_steps = int(p.get("max_steps", 1))
    except Exception:
        max_steps = 1

    # [T07-02-01] max_steps<=0 → 呼ばれない
    if max_steps <= 0:
        return ""

    # 正規化
    try:
        msgs = _normalize_messages(messages_in)
    except Exception:
        return ""

    # 連結
    try:
        text = _join_contents(msgs)
    except Exception:
        text = ""

    # 分割（例外吸収 & 空チャンクは呼ばない）
    try:
        max_chars = p.get("max_chars", 1000)
        chunks = textsplit.split_text(text, max_chars=max_chars, split_sentences=False)
    except Exception:
        # [T07-02-03] textsplit 例外 → 呼ばれない
        return ""

    if not chunks or all((not c) for c in chunks):
        # [T07-02-02] 空チャンク → 呼ばれない
        return ""

    # 実行（steps 上限を守る）
    taken = 0
    last: Any = ""
    for ch in chunks:
        if taken >= max_steps:
            break
        # テストで chat_loop.chat が patch される（policy.chat_fn バイパスも chat_loop 側責務）
        last = chat_loop.chat(ch, policy=p, **extra)  # type: ignore[attr-defined]
        taken += 1

    return "" if last is None else str(last)
