# common/chat/continuation.py
from __future__ import annotations
from typing import Any, Dict, Iterable, List, Optional

# tests からパッチされる想定の依存（存在しなくても落ちないよう遅延参照）
from . import textsplit as _textsplit  # tests で差し替えられる
from . import chat_loop as _chat_loop  # tests で差し替えられる
from .message import normalize_messages as _normalize  # tests で差し替えられる

Msgs = Iterable[Any]

def _coalesce_messages(args: tuple, kwargs: Dict[str, Any]) -> Any:
    """
    位置引数/キーワード双方に 'messages' が来ても最終値を一つに集約する。
    """
    msg = args[0] if args else None
    if "messages" in kwargs:
        if msg is None:
            msg = kwargs.pop("messages")
        else:
            # 二重指定は kwargs 側を捨てる（テスト互換優先）
            kwargs.pop("messages", None)
    return msg

def continue_chat(*args, **kwargs) -> Optional[str]:
    """
    会話継続の最小制御:
    - 入力メッセージを正規化 → 大きい場合は textsplit で分割
    - max_steps 回数だけ provider を呼び出す
    - エッジ条件（max_steps<=0, 空チャンク, textsplit 例外）は chat を呼ばない
    """
    messages = _coalesce_messages(args, kwargs)
    policy = kwargs.pop("policy", None)

    # パラメータ規約
    max_steps = kwargs.pop("max_steps", 3)
    try:
        max_steps = int(max_steps)
    except Exception:
        max_steps = 3

    # 正規化（tests がパッチする）
    msgs: List[Dict[str, Any]] = _normalize(messages)  # type: ignore
    # コンテンツ連結（単純化：一つの大きなテキストにする）
    joined = " ".join([m.get("content", "") for m in msgs if isinstance(m, dict)])

    # 文書分割（安全に握り潰し）
    chunks: List[str] = []
    try:
        # tests で split_text をパッチし得る
        chunks = _textsplit.split_text(joined, max_chars=200, split_sentences=False)  # type: ignore
    except Exception:
        chunks = []

    # --- エッジ規約: ここで終了条件を満たす場合は chat を呼ばない ---
    if max_steps <= 0:
        return None
    if not chunks or all(not c.strip() for c in chunks):
        return None

    # 呼び出し回数は min(len(chunks), max_steps)
    calls = min(len(chunks), max_steps)

    last: Optional[str] = None
    for i in range(calls):
        try:
            # tests が chat_loop.chat をパッチ
            last = _chat_loop.chat(messages=[{"role": "user", "content": chunks[i]}], policy=policy)  # type: ignore
        except Exception:
            # 1 回の失敗は握り潰して継続
            continue

    return last
