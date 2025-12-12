"""
common.chat.sharing

T08-01 / T08-02 のテスト仕様をすべて満たすための共有モジュール。
"""

from __future__ import annotations
import json
import copy
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union

from common.session import server_session_manager as server_session_manager

SSM = server_session_manager.ServerSessionManager
_CURRENT_VERSION = 1

# -------------------------------
# 内部型
# -------------------------------
@dataclass
class _NormalizedSession:
    version: int
    session_id: Optional[str]
    ts: Optional[int]
    provider: Optional[str]
    model: Optional[str]
    messages: List[Any]
    meta: Dict[str, Any]


def _to_int_or_none(v: Any) -> Optional[int]:
    try:
        return int(v)
    except Exception:
        return None


# -------------------------------
# 旧形式の正規化
# -------------------------------
def _normalize_legacy_session(obj: Dict[str, Any]) -> _NormalizedSession:
    if not isinstance(obj, dict):
        return _NormalizedSession(
            version=_CURRENT_VERSION,
            session_id=None,
            ts=None,
            provider=None,
            model=None,
            messages=[],
            meta={},
        )

    raw_version = obj.get("version")
    ver = _to_int_or_none(raw_version)

    # v0 JSON の場合
    if ver == 0 and isinstance(obj.get("session"), dict):
        base = obj["session"]
    else:
        base = obj

    if not isinstance(base, dict):
        base = {}

    session_id = base.get("id") or base.get("session_id")
    ts = base.get("ts") or base.get("timestamp")

    provider = base.get("provider") if isinstance(base.get("provider"), str) else None
    model = base.get("model") if isinstance(base.get("model"), str) else None
    messages = base.get("messages") or base.get("history") or []
    if not isinstance(messages, list):
        messages = []

    meta_raw = base.get("meta")
    meta = copy.deepcopy(meta_raw) if isinstance(meta_raw, dict) else {}

    return _NormalizedSession(
        version=_CURRENT_VERSION,
        session_id=session_id,
        ts=_to_int_or_none(ts),
        provider=provider,
        model=model,
        messages=messages,
        meta=meta,
    )


def _normalized_to_export_dict(ns: _NormalizedSession) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "version": ns.version,
        "id": ns.session_id,
        "ts": ns.ts,
        "messages": copy.deepcopy(ns.messages),
    }
    if ns.provider:
        out["provider"] = ns.provider
    if ns.model:
        out["model"] = ns.model
    if ns.meta:
        out["meta"] = copy.deepcopy(ns.meta)
    return out


def _sanitize_import_dict(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not isinstance(data, dict):
        return None
    if not isinstance(data.get("messages"), list):
        return None

    out = {
        "version": _CURRENT_VERSION,
        "id": data.get("id"),
        "ts": data.get("ts"),
        "messages": copy.deepcopy(data["messages"]),
    }

    if isinstance(data.get("provider"), str):
        out["provider"] = data["provider"]
    if isinstance(data.get("model"), str):
        out["model"] = data["model"]
    if isinstance(data.get("meta"), dict):
        out["meta"] = copy.deepcopy(data["meta"])

    return out


# -------------------------------
# 公開 API
# -------------------------------

def export_session(session: Dict[str, Any]) -> str:
    """
    T08-01-01 の仕様：戻り値は dict ではなく JSON 文字列
    """
    if not isinstance(session, dict):
        base = {}
    else:
        base = session

    ns = _normalize_legacy_session(base)
    data = _normalized_to_export_dict(ns)

    # JSON文字列で返す
    return json.dumps(data, ensure_ascii=False)


def import_session(data: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    不正 JSON → 空セッション dict を返す（T08-01-04）
    """
    if isinstance(data, dict):
        obj = data
    else:
        try:
            obj = json.loads(data)
        except Exception:
            print("sharing.import_session: invalid JSON")
            # T08-01-04 に合わせ dict を返す
            return {"version": _CURRENT_VERSION, "messages": []}

    if not isinstance(obj, dict):
        return {"version": _CURRENT_VERSION, "messages": []}

    ns = _normalize_legacy_session(obj)
    normalized = _normalized_to_export_dict(ns)

    sanitized = _sanitize_import_dict(normalized)
    if sanitized is None:
        return {"version": _CURRENT_VERSION, "messages": []}

    return sanitized


# -------------------------------
# ギルド共有
# -------------------------------

def _share_to_server_impl(*, guild_id: int, session: Dict[str, Any]) -> None:
    """
    T08-01-03 の @patch 対象。
    実処理は share_to_guild() 側で行われる。
    """
    manager = SSM()
    if hasattr(manager, "share_to_guild"):
        manager.share_to_guild(guild_id=guild_id, session=session)


def share_to_guild(*, guild_id: int, session: Dict[str, Any]) -> None:
    """
    テストは _share_to_server_impl をパッチして呼び出し確認する。
    """
    _share_to_server_impl(guild_id=guild_id, session=session)
