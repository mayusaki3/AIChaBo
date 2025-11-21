# common/chat/textsplit.py
# -*- coding: utf-8 -*-
"""
TextSplit Utility

要件:
- split_text(text, max_chars, split_sentences=False) を提供
- T06-01/T06-02 の仕様に適合:
  - split_sentences=True のときは「文単位で返す」。文と文を一つに詰めて再結合しない
  - 英文は ". "（終端記号 + 半角空白）を優先して文切り出し
  - 和文は「。！？（全角）」で終端する文に分割
  - split_sentences=False のときは、原文（改行/CRLF を含む）を **そのまま固定長スライス** する
    → 連結すると必ず原文と一致する（保存性）
  - max_chars は int 以外で TypeError、0以下で ValueError
  - テスト側の「関数を self 属性に束縛して呼ぶ」形式（擬似メソッド呼び）にも耐性

公開関数:
    split_text(*args, **kwargs) -> List[str]
"""

from typing import List, Iterable, Tuple
import re

# 英文切り出し: 終端記号 [.!?] の直後に続く「1個以上の空白」を区切りと見なす
# 例: "Hello. World." -> ["Hello.", "World."]
_RE_SPLIT_EN = re.compile(r"(?<=[.!?])\s+")

# 和文切り出し: 「。！？（全角）」を終端とみなし、終端は文に含めて返す
_RE_JA_END = re.compile(r"[。！？]")

def _parse_args(args: tuple, kwargs: dict) -> Tuple[str, int, bool]:
    """
    呼び出し互換性レイヤ:
    - テストで self.split = split_text と束縛された場合でも動作させる
    - 受理パターン:
        split_text("abc", 50, True)
        split_text("abc", max_chars=50, split_sentences=True)
        self.split("abc", 50, True)
    """
    if not args:
        raise TypeError("text is required")

    # 先頭が文字列でなければ 2番目を text と見なす（self バインド対策）
    if isinstance(args[0], str):
        text = args[0]
        rest = list(args[1:])
    else:
        if len(args) < 2 or not isinstance(args[1], str):
            raise TypeError("text is required")
        text = args[1]
        rest = list(args[2:])

    # max_chars
    if "max_chars" in kwargs:
        max_chars = kwargs["max_chars"]
    elif rest:
        max_chars = rest.pop(0)
    else:
        max_chars = 2000  # デフォルト保険（テストでは明示指定される想定）

    # split_sentences
    if "split_sentences" in kwargs:
        split_sentences = bool(kwargs["split_sentences"])
    elif rest:
        split_sentences = bool(rest.pop(0))
    else:
        split_sentences = False

    if not isinstance(max_chars, int):
        raise TypeError("max_chars must be int")
    if max_chars <= 0:
        raise ValueError("max_chars must be > 0")

    return text, max_chars, split_sentences


# ---------------- 文単位分割 ----------------

def _split_sentences_en(text: str) -> List[str]:
    """
    英文を文単位で返す。
    区切り規則: [.!?] の後ろに 1個以上の空白が来た箇所で区切る。
    ※ 最終文の末尾に空白が無くても、そのまま 1文として返る。
    """
    parts = _RE_SPLIT_EN.split(text)
    # 余計な空要素は除去。各文は左右の空白を落とす（先頭空白を残さない）
    out = [p.strip() for p in parts if p and p.strip() != ""]
    return out if out else [text]  # 一切区切れない場合は全文1要素


def _split_sentences_ja(text: str) -> List[str]:
    """
    和文を文単位で返す。終端記号（。！？）は文に含める。
    例: "今日は晴れ。明日も晴れ！ね？" -> ["今日は晴れ。", "明日も晴れ！", "ね？"]
    """
    out: List[str] = []
    buf = []
    for ch in text:
        buf.append(ch)
        if _RE_JA_END.fullmatch(ch):
            raw = "".join(buf)
            s = raw.strip()
            # 「空白＋終端のみ」なら捨てる（ガード枝）
            # 例: "　。" / "   ！" など -> append しない
            if s and _RE_JA_END.sub("", s).strip() != "":
                out.append(s)
            buf = []
    # 終端記号で終わらない残り
    tail = "".join(buf).strip()
    if tail:
        out.append(tail)
    # out が空（= 全体が空白＋終端のみ 等）の場合は空配列のまま返す
    return out


def _split_sentences(text: str) -> List[str]:
    """
    多言語テキストに対して、まず英文規則で試し、効果が弱ければ和文規則で再評価。
    - 英文規則で 2文以上に分かれたらそれを採用
    - そうでなければ和文規則を適用
    """
    en = _split_sentences_en(text)
    if len(en) >= 2:
        return en
    return _split_sentences_ja(text)


def _hard_cut(s: str, max_chars: int) -> Iterable[str]:
    """1つの文/断片が max_chars を超える場合にハード分割する。"""
    for i in range(0, len(s), max_chars):
        yield s[i:i + max_chars]


# ---------------- 固定長スライス（保存モード） ----------------

def _fixed_slice(text: str, max_chars: int) -> List[str]:
    """
    原文保存モード: 改行/CRLF を一切正規化せず、そのまま固定長スライス。
    これにより `"".join(chunks) == text` が常に成り立つ。
    """
    return [text[i:i + max_chars] for i in range(0, len(text), max_chars)] if text else []


# ---------------- 公開API ----------------

def split_text(*args, **kwargs) -> List[str]:
    """
    汎用分割関数。
    - split_sentences=True: 文単位で **そのまま** 返す（チャンク詰め込みで再結合しない）
        各文が max_chars を超える場合は、その文だけハード分割する。
    - split_sentences=False: 原文保存の固定長スライス。CRLF/改行・空白などを一切変更しない。
    """
    text, max_chars, split_sentences = _parse_args(args, kwargs)

    if text == "":
        return []

    if split_sentences:
        # 文単位列を作り、各要素ごとに max_chars を適用（再結合しない）
        sentences = _split_sentences(text)
        out: List[str] = []
        for s in sentences:
            if len(s) <= max_chars:
                out.append(s)
            else:
                out.extend(_hard_cut(s, max_chars))
        return out

    # 保存モード（固定長スライス）
    return _fixed_slice(text, max_chars)
