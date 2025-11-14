# common/chat/textsplit.py
"""
Text splitting utilities (Unicode char based).

Public API:
    split_text(text: str, *, max_chars: int = 500, split_sentences: bool = False) -> list[str]

Notes
- 分割単位は Unicode 文字数（トークンではない）
- 文分割は簡易ルール（和文: 。．！？ / 英文: '.' の後が空白 or 行末）
- テスト側でクラス属性にバインドされ self 経由で呼ばれても動くように、先頭の
  余分な位置引数を無視する吸収ロジックを持つ
"""

from __future__ import annotations
from typing import List, Tuple

__all__ = ["split_text"]

# 文末候補の記号
_SENT_END_CHARS = {"。", "．", "！", "？", "!", "?"}


def _chunk_by_chars(s: str, max_chars: int) -> List[str]:
    if max_chars <= 0:
        raise ValueError("max_chars must be > 0")
    if not s:
        return []
    out: List[str] = []
    buf: List[str] = []
    cur = 0
    for ch in s:
        buf.append(ch)
        cur += 1
        if cur >= max_chars:
            out.append("".join(buf))
            buf, cur = [], 0
    if buf:
        out.append("".join(buf))
    return out


def _split_sentences(s: str) -> List[str]:
    """正規表現の後読みを使わずに文境界を検出。"""
    if not s:
        return []
    parts: List[str] = []
    start = 0
    i = 0
    n = len(s)
    while i < n:
        ch = s[i]
        boundary = False
        cut_pos = i + 1

        if ch in _SENT_END_CHARS:
            boundary = True
        elif ch == ".":
            nxt = s[i + 1] if i + 1 < n else ""
            if (not nxt) or nxt.isspace():
                boundary = True

        if boundary:
            parts.append(s[start:cut_pos])
            start = cut_pos
        i += 1

    if start < n:
        parts.append(s[start:])
    return parts


def _unpack_args_kwargs(args: Tuple, kwargs: dict) -> Tuple[str, int, bool]:
    """
    テストが self.split(...) の形で呼ぶため、先頭に余分な位置引数(self)が
    入っても受け止めて正しい引数に復元する。
    """
    # text の取得
    text = None
    if "text" in kwargs:
        text = kwargs.pop("text")
    elif args:
        # args[0] が self の可能性を考慮
        if isinstance(args[0], str):
            text = args[0]
            args = args[1:]
        elif len(args) >= 2 and isinstance(args[1], str):
            text = args[1]
            args = args[2:]
        else:
            # self だけ渡っている / 型不正など
            raise TypeError("split_text: invalid positional arguments for 'text'")

    if not isinstance(text, str):
        raise TypeError("text must be str")

    # パラメータ
    max_chars = kwargs.pop("max_chars", 500)
    # 将来の表記ゆれ対策（テストでは使っていないが安全側）
    if "max_len" in kwargs and "max_chars" not in kwargs:
        max_chars = kwargs.pop("max_len")

    split_sentences = kwargs.pop("split_sentences", False)

    # 予期しない追加引数は拒否
    if args or kwargs:
        raise TypeError("split_text: unexpected extra arguments")

    return text, int(max_chars), bool(split_sentences)


def split_text(*args, **kwargs) -> List[str]:
    """
    文字数ベースでテキストを分割する。テスト側の self バインド呼び出しにも対応。

    Usage:
        split_text(text, *, max_chars=500, split_sentences=False)
    """
    text, max_chars, wants_sentence = _unpack_args_kwargs(args, kwargs)

    if max_chars <= 0:
        raise ValueError("max_chars must be > 0")
    if text == "":
        return []

    if wants_sentence:
        seeds = _split_sentences(text)
        chunks: List[str] = []
        for seed in seeds:
            if len(seed) <= max_chars:
                chunks.append(seed)
            else:
                chunks.extend(_chunk_by_chars(seed, max_chars))
        return chunks

    return _chunk_by_chars(text, max_chars)
