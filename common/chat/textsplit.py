# common/chat/textsplit.py
# - 変更点:
#   1) max_chars の型チェックを追加: int 以外なら TypeError
#   2) max_chars の下限チェック: < 1 は ValueError
#   3) 文分割時は各チャンクを strip() して先頭/末尾の空白を除去
#   4) 空チャンクは除外

import re
from typing import List

# 句点・感嘆・疑問、または ". " パターンでの文境界
_SENTENCE_SPLIT = re.compile(r"(?<=[。．！？!?])|(?<=\.\s)")

def _split_sentences(text: str) -> List[str]:
    # 正規表現 split は区切り記号を消費しないため、そのまま分かれる
    parts = _SENTENCE_SPLIT.split(text)
    # 余計な空白を除去し、空要素は落とす
    out: List[str] = []
    for p in parts:
        t = p.strip()
        if not t:
            continue
        out.append(t)
    return out

def split_text(
    text: str,
    *,
    max_chars: int = 1000,
    split_sentences: bool = False,
) -> List[str]:
    if not isinstance(max_chars, int):
        raise TypeError("max_chars must be int")
    if max_chars < 1:
        raise ValueError("max_chars must be >= 1")

    if not text:
        return []

    # 文単位要求があればまず文に分割
    units = _split_sentences(text) if split_sentences else [text]

    chunks: List[str] = []
    for unit in units:
        # unit を max_chars 以内にハード分割
        start = 0
        L = len(unit)
        while start < L:
            end = min(start + max_chars, L)
            chunks.append(unit[start:end])
            start = end
    return chunks
