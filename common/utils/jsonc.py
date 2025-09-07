# common/utils/jsonc.py
from __future__ import annotations
from pathlib import Path
import json

def _strip_comments_and_trailing_commas(text: str) -> str:
    """JSONC -> JSON へ変換。//, #, /*...*/ を除去し、文字列外の末尾カンマも除去。"""
    out = []
    i, n = 0, len(text)
    IN_STR = False
    ESC = False
    BLOCK = False  # /* ... */
    LINE = False   # //... or #...
    str_delim = '"'

    while i < n:
        ch = text[i]
        nxt = text[i+1] if i+1 < n else ""

        if IN_STR:
            out.append(ch)
            if ESC:
                ESC = False
            elif ch == "\\":
                ESC = True
            elif ch == str_delim:
                IN_STR = False
            i += 1
            continue

        if BLOCK:
            if ch == "*" and nxt == "/":
                BLOCK = False
                i += 2
            else:
                i += 1
            continue

        if LINE:
            if ch in ("\r", "\n"):
                LINE = False
                out.append(ch)
            i += 1
            continue

        if ch == '"':
            IN_STR = True
            out.append(ch)
            i += 1
            continue

        if ch == "/" and nxt == "*":
            BLOCK = True
            i += 2
            continue
        if ch == "/" and nxt == "/":
            LINE = True
            i += 2
            continue
        if ch == "#":
            LINE = True
            i += 1
            continue

        out.append(ch)
        i += 1

    s = "".join(out)

    # 末尾カンマの除去（文字列外のみ対象）
    out2 = []
    i, n = 0, len(s)
    IN_STR = False
    ESC = False
    while i < n:
        ch = s[i]
        if IN_STR:
            out2.append(ch)
            if ESC:
                ESC = False
            elif ch == "\\":
                ESC = True
            elif ch == '"':
                IN_STR = False
            i += 1
            continue
        if ch == '"':
            IN_STR = True
            out2.append(ch)
            i += 1
            continue
        if ch == ",":
            j = i + 1
            while j < n and s[j] in " \t\r\n":
                j += 1
            if j < n and s[j] in "]}":
                i += 1
                continue  # カンマを落とす
        out2.append(ch)
        i += 1

    return "".join(out2)

def loads_jsonc(text: str):
    return json.loads(_strip_comments_and_trailing_commas(text))

def load_jsonc(path: str | Path):
    p = Path(path)
    return loads_jsonc(p.read_text(encoding="utf-8"))
