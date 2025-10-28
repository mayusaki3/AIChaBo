# common/chat/textsplit.py
# ------------------------------------------------------------
# 送信プラットフォームの文字数上限に合わせて文字列を安全に分割するユーティリティ。
# ※ 上限値は“呼び出し側（Discord/Slack/CLI など）”で決め、引数 limit として渡す。
# ------------------------------------------------------------
from __future__ import annotations

def split_text(
    text: str,
    *,
    limit: int,
    preserve_lines: bool = True,
) -> list[str]:
    """
    上限文字数 limit に合わせて text を分割する。

    ポリシー:
      1) preserve_lines=True の場合、まず行単位で“できるだけ区切る”
      2) それでも超える塊は、文字数で強制分割（安全側）

    Args:
        text: 分割対象文字列
        limit: 送信先の文字数上限（例: Discord=2000, Slack ≈4000 など）
        preserve_lines: 行境界を優先して分割（可読性のため推奨）

    Returns:
        分割済み文字列のリスト（空文字や None は返さない）
    """
    if not text:
        return []
    if limit is None or limit <= 0:
        raise ValueError("split_text: 'limit' must be a positive integer")

    # まずは単純ケース
    if len(text) <= limit:
        return [text]

    # 1) 行単位でできるだけ詰める
    parts: list[str] = []
    if preserve_lines:
        buf = ""
        for line in text.splitlines(keepends=True):
            if len(buf) + len(line) > limit:
                if buf:
                    parts.append(buf)
                    buf = ""
                # 1行が極端に長い場合は次段で強制分割
                if len(line) > limit:
                    _force = [line[i : i + limit] for i in range(0, len(line), limit)]
                    parts.extend(_force[:-1])
                    buf = _force[-1]
                else:
                    buf = line
            else:
                buf += line
        if buf:
            parts.append(buf)
    else:
        parts = [text]

    # 2) なお大きい塊は強制分割
    normalized: list[str] = []
    for p in parts:
        if len(p) <= limit:
            normalized.append(p)
        else:
            normalized.extend(p[i : i + limit] for i in range(0, len(p), limit))

    return normalized
