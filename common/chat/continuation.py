# common/chat/continuation.py
# ------------------------------------------------------------
# 「続けます」「少々お待ちください」等の“継続予告フレーズ”を、
# 実際に続きの投稿をしない場合はユーザー誘導文へ置換するユーティリティ。
# Discord/Slack/CLI など送信先に依らず再利用できる“文言整形”のみを担当。
# ------------------------------------------------------------
from __future__ import annotations
import re
from typing import Iterable

# 置換対象フレーズの既定パターン
# - 必要に応じて他言語・他表現を追加可
_DEFAULT_CONTINUE_PAT = re.compile(
    r"(すぐに続けますね。?|少々お待ちください。?|続けますね。?|続けます。?|続きます。?)"
)

def sanitize_continuation_phrases(
    text: str,
    will_auto_continue: bool,
    *,
    # 呼び出し側で独自パターンに差し替えたい場合のフック
    pattern: re.Pattern[str] | None = None,
    replace_with: str = "続けますか？（必要なら『続けて』と送ってください）",
) -> str:
    """
    継続投稿が“自動では行われない”場合に、予告フレーズをユーザー誘導に置換する。

    Args:
        text: 整形対象文字列
        will_auto_continue: True のとき置換しない（実際に続き投稿を行う前提）
        pattern: 置換対象の正規表現パターン（未指定なら既定 _DEFAULT_CONTINUE_PAT）
        replace_with: 置換後のメッセージ

    Returns:
        置換後文字列（置換不要時はそのまま返す）
    """
    if not isinstance(text, str) or not text:
        return text
    if will_auto_continue:
        return text
    pat = pattern or _DEFAULT_CONTINUE_PAT
    return pat.sub(replace_with, text)
