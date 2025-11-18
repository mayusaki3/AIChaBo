# -*- coding: utf-8 -*-
"""
Continuation flow

要点:
- messages 正規化後、textsplit で分割し chat_loop へ逐次投入
- max_steps<=0 / 空チャンク / textsplit 例外時は chat_loop を呼ばない
- モジュール属性として chat_loop を公開（テストの patch 対象）
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional, Iterable, Union

# テストで patch されるためモジュール属性として import（名前を露出）
from . import chat_loop  # noqa: F401
from . import message as message_mod
from . import textsplit as textsplit_mod

MessageLike = Union[str, Dict[str, Any]]
MessagesInput = Union[MessageLike, Iterable[MessageLike]]

def _to_list(messages: MessagesInput) -> List[Dict[str, Any]]:
    return message_mod.normalize_messages(messages)

def _join_contents(msgs: List[Dict[str, Any]]) -> str:
    # 最小限: content を順に結合（provider 振る舞いは別層テスト）
    contents = [m.get("content") for m in msgs if isinstance(m, dict)]
    return message_mod.join_messages([c for c in contents if isinstance(c, str)])

def continue_chat(
    messages: MessagesInput,
    *,
    policy: Optional[Dict[str, Any]] = None,
    **extra: Any,
) -> str:
    """
    連続チャットの薄い制御。
    - 正規化 → 連結 → 分割 → chat_loop.chat を順次呼び出し
    - 例外/境界条件では安全に早期終了
    :param messages: str / dict / それらの反復
    :param policy: provider/model 等（任意）
    :return: 最終応答文字列（最低限の実装）
    """
    # policy ガード（Noneでも落ちない）
    max_steps = 1
    if isinstance(policy, dict):
        try:
            max_steps = int(policy.get("max_steps", 1))
        except Exception:
            max_steps = 1

    # [T07-02-01] max_steps==0 → 呼ばれない
    if max_steps <= 0:
        return ""

    # 正規化
    try:
        msgs = _to_list(messages)
    except Exception:
        return ""

    # 連結
    try:
        text = _join_contents(msgs)
    except Exception:
        text = ""

    # 分割（例外吸収 & 空チャンクは呼ばない）
    try:
        chunks = textsplit_mod.split_text(text, max_chars=policy.get("max_chars", 1000) if isinstance(policy, dict) else 1000, split_sentences=False)
    except Exception:
        # [T07-02-03] textsplit 例外 → 呼ばれない
        return ""

    if not chunks or all((not c) for c in chunks):
        # [T07-02-02] 空チャンク → 呼ばれない
        return ""

    # 実行（steps 上限を守る）
    taken = 0
    last = ""
    for ch in chunks:
        if taken >= max_steps:
            break
        # テストで chat_loop.chat が patch される
        last = chat_loop.chat(ch, policy=policy, **extra)  # type: ignore[attr-defined]
        taken += 1

    return "" if last is None else str(last)
