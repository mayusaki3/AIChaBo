# -*- coding: utf-8 -*-
"""
Message utilities for chat modules.

公開I/F（テストが参照）:
- normalize_messages (alias: normalize, to_messages)
- join_messages (alias: join)
- add_role_default (alias: ensure_role)

設計方針:
- 文字列/配列/辞書の入力を [{role, content}] へ正規化
- role 未指定は "user" を補完
- content 欠落/非文字列要素はスキップ
- 配列結合ユーティリティを提供
- テストがクラス属性へバインドしても self が注入されないよう、
  関数は callable オブジェクトとしてエクスポートする
"""

from typing import Any, Dict, Iterable, List, Sequence, Union, Optional

Message = Dict[str, Any]
Messages = List[Message]


# ---- 実体実装 ---------------------------------------------------------------

def _coerce_one(obj: Any) -> Optional[Message]:
    """
    単一要素をメッセージに変換。
    - str -> {"role":"user","content":stripped}
    - dict -> {"role":..., "content":...}  (roleは後段で補完)
    - それ以外は None（スキップ対象）
    """
    if isinstance(obj, str):
        return {"role": "user", "content": obj.strip()}
    if isinstance(obj, dict):
        if "content" not in obj:
            return None
        return dict(obj)
    return None


def _add_role_default_impl(messages: Sequence[Message], default_role: str = "user") -> Messages:
    """
    role 未指定のメッセージに既定ロールを補完する。
    注意: dict を防御的にコピーして返す。
    """
    out: Messages = []
    for m in messages:
        if not isinstance(m, dict):
            continue
        role = m.get("role", default_role)
        out.append({"role": role, "content": m.get("content")})
    return out


def _normalize_messages_impl(src: Union[str, Message, Sequence[Any]]) -> Messages:
    """
    入力を [{role, content}] 配列に正規化する。

    許可入力:
      - str
      - dict（要 content）
      - list/tuple[...]（要素は str または dict を許容）
    それ以外は TypeError
    """
    if src == "":
        return [{"role": "user", "content": ""}]

    if isinstance(src, str):
        return [{"role": "user", "content": src.strip()}]

    if isinstance(src, dict):
        one = _coerce_one(src)
        if one is None:
            return []
        return _add_role_default_impl([one])

    if isinstance(src, (list, tuple)):
        acc: Messages = []
        for x in src:
            one = _coerce_one(x)
            if one is None:
                continue
            acc.append(one)
        return _add_role_default_impl(acc)

    raise TypeError("unsupported message input type")


def _join_messages_impl(messages: Iterable[Message], sep: str = "") -> str:
    """
    メッセージ配列を content で連結して返す。
    - content が文字列でない要素はスキップ
    """
    parts: List[str] = []
    for m in messages:
        c = m.get("content")
        if isinstance(c, str):
            parts.append(c)
    return sep.join(parts)


# ---- 記述子バインドを避けるための callable ラッパ ---------------------------

class _Fn:
    __slots__ = ("_f",)
    def __init__(self, f):
        self._f = f
    def __call__(self, *args, **kwargs):
        return self._f(*args, **kwargs)


# ---- 公開シンボル（callable オブジェクトとしてエクスポート） ---------------

normalize_messages = _Fn(_normalize_messages_impl)
normalize = normalize_messages
to_messages = normalize_messages

join_messages = _Fn(_join_messages_impl)
join = join_messages

add_role_default = _Fn(_add_role_default_impl)
ensure_role = add_role_default
