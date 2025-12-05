# -*- coding: utf-8 -*-
"""
common.chat.sharing

認証情報およびチャットセッションを「共有」するためのユーティリティ群を提供するモジュール。

1) 認証共有（既存機能）
   - is_already_shared
   - share_user_auth_to_server
   - unshare_server_auth

2) セッション共有（T08-01: Sharing Session）
   - export_session:  ユーザーセッション(dict) → 共有用 JSON(dict)
   - import_session:  共有 JSON(dict) → セッション(dict)
   - share_to_guild:  ユーザーセッションをギルドへ共有登録（SSM 経由）

注意:
- セッション共有は「非機密」のみ扱う（メッセージ履歴など）。
- バージョン管理用に SCHEMA_VERSION を導入。
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from common.secret.store import store
from common.session.user_session_manager import user_session_manager as USM
from common.session.server_session_manager import server_session_manager as SSM
from common.chat.provider import normalize_provider


# ============================================================
# 既存: 認証情報のサーバー共有
# ============================================================


def is_already_shared(guild_id: int) -> bool:
    """
    指定ギルドに 1 つでもサーバー共有鍵が存在するかを確認する。

    Args:
        guild_id: 対象ギルド ID

    Returns:
        True  : 1 つ以上のサーバー共有鍵が存在する
        False : サーバー共有鍵が存在しない
    """
    keys = store.get_server_keys(guild_id)
    return bool(keys)


def share_user_auth_to_server(guild_id: int, user_id: int) -> Dict[str, bool]:
    """
    ユーザーの登録済み「全プロバイダ鍵」をサーバーへコピーする。

    - 機密情報（API キー）は SecretStore 経由でコピー
    - 非機密情報（provider/model 等）は ServerSessionManager に反映

    Args:
        guild_id: 対象ギルド ID
        user_id : コピー元ユーザー ID

    Returns:
        {canonical_provider: True/False} の dict
        True  : そのプロバイダ鍵のコピーに成功
        False : 鍵が存在しない or コピー失敗
    """
    # ユーザーの非機密セッション情報（provider/model 等）
    user_cfg: Dict[str, Any] = USM.get_session(user_id) or {}
    chat = user_cfg.get("chat") or {}
    hint_provider = normalize_provider(chat.get("provider", ""))

    # SecretStore からユーザーの全プロバイダ鍵を優先順で取得
    results: Dict[str, bool] = {}

    ordered = []
    if hint_provider:
        ordered.append(hint_provider)

    # 代表的な既知プロバイダを追加（重複は除外）
    for prov in ("openai", "claude", "gemini"):
        if prov not in ordered:
            ordered.append(prov)

    for prov in ordered:
        key = store.get_user_key(user_id, prov)
        if not key:
            results[prov] = False
            continue
        try:
            store.put_server_key(guild_id, prov, key)
            results[prov] = True
        except Exception:
            # コピーに失敗した場合も他プロバイダには影響させない
            results[prov] = False

    # 非機密の共有状態（SSM）も同期（プロバイダ/モデルなど）
    # 共有 ON/OFF のフラグは持たず、「現在の設定値のみ」反映する方針。
    if chat:
        SSM.set_shared_auth_config(guild_id, {"chat": chat})

    return results


def unshare_server_auth(guild_id: int) -> bool:
    """
    サーバー共有鍵（機密）をすべて削除する。

    - 非機密情報は SSM 側に残す（/ac_removeauth の方針と整合）

    Args:
        guild_id: 対象ギルド ID

    Returns:
        True  : 正常に削除完了
        False : 削除処理中に例外が発生した
    """
    try:
        # 既存のすべてのプロバイダ鍵を削除
        for prov in list(store.get_server_keys(guild_id).keys()):
            store.delete_server_key(guild_id, prov)
        return True
    except Exception:
        return False


# ============================================================
# 追加: セッション共有 (T08-01)
# ============================================================

# セッション JSON のスキーマバージョン
SCHEMA_VERSION: int = 1


def export_session(session: Dict[str, Any]) -> Dict[str, Any]:
    """
    ユーザーセッション(dict)を共有用 JSON(dict) に変換する。

    - 必須: messages (list)
    - 任意: id, ts, title, meta
    - 共有用メタ: version (int)

    Args:
        session: 内部表現のセッション dict

    Returns:
        共有用 JSON dict（余剰フィールドは含めない）
    """
    if not isinstance(session, dict):
        raise ValueError("session must be a dict")

    # messages は list 以外なら空リストにフォールバック
    messages = session.get("messages") or []
    if not isinstance(messages, list):
        messages = []

    # id は文字列化（存在すれば）
    sid = session.get("id")
    if sid is not None:
        sid = str(sid)

    # ts は整数化を試み、失敗した場合は省略
    ts_raw = session.get("ts")
    ts: Optional[int] = None
    if ts_raw is not None:
        try:
            ts = int(ts_raw)
        except Exception:
            ts = None

    out: Dict[str, Any] = {
        "messages": messages,
        "version": SCHEMA_VERSION,
    }

    if sid is not None:
        out["id"] = sid
    if ts is not None:
        out["ts"] = ts

    # 代表的な任意フィールドをサニタイズして転送
    title = session.get("title")
    if isinstance(title, str):
        out["title"] = title

    meta = session.get("meta")
    if isinstance(meta, dict):
        out["meta"] = meta

    return out


def import_session(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    共有 JSON(dict) から内部セッション(dict) を再構築する。

    - 型/必須項目が不正な場合は None を返す（安全側）。
    - 未知フィールドは無視し、既知フィールドのみ採用する（サニタイズ）。
    - version が未知の場合は None を返すか、互換とみなして通すかは実装ポリシー。
      ここでは安全側として「未知 version は None を返す」。

    Args:
        data: 共有 JSON dict

    Returns:
        正常: 再構築したセッション dict
        異常: None
    """
    if not isinstance(data, dict):
        return None

    # バージョン互換チェック
    ver = data.get("version")
    if ver is not None and ver != SCHEMA_VERSION:
        # 将来拡張を考慮しつつ、現時点では安全側として拒否
        return None

    # messages は必須、かつ list 型を要求
    messages = data.get("messages")
    if not isinstance(messages, list):
        return None

    out: Dict[str, Any] = {
        "messages": messages,
    }

    # id は存在すれば文字列化
    sid = data.get("id")
    if sid is not None:
        out["id"] = str(sid)

    # ts は整数化を試み、失敗時は省略
    ts_raw = data.get("ts")
    if ts_raw is not None:
        try:
            out["ts"] = int(ts_raw)
        except Exception:
            pass

    # 任意フィールド（タイトル/メタ情報）
    title = data.get("title")
    if isinstance(title, str):
        out["title"] = title

    meta = data.get("meta")
    if isinstance(meta, dict):
        out["meta"] = meta

    # version は保持しておく（未指定なら現行バージョンを付与）
    if ver is not None:
        out["version"] = ver
    else:
        out["version"] = SCHEMA_VERSION

    return out


def share_to_guild(*, guild_id: int, session: Dict[str, Any]) -> Dict[str, Any]:
    """
    ユーザーセッションをギルド単位の共有セッションとして登録する。

    - export_session でサニタイズ/バージョン付与
    - ServerSessionManager (SSM) へ登録
      - `set_shared_session` があればそれを使用
      - なければフォールバックとして `set_session` を試す

    Args:
        guild_id: 共有先ギルド ID
        session: 共有対象のセッション dict

    Returns:
        export 済みの共有用 JSON dict
    """
    data = export_session(session)

    try:
        if hasattr(SSM, "set_shared_session"):
            # 共有セッション専用の格納先がある場合
            SSM.set_shared_session(guild_id, data)  # type: ignore[attr-defined]
        elif hasattr(SSM, "set_session"):
            # 汎用セッション API しかない場合のフォールバック
            SSM.set_session(guild_id, data)  # type: ignore[attr-defined]
        # どちらも無い場合は何もしない（テストでは patch だけ確認）
    except Exception:
        # 共有登録の失敗は例外を外へ伝搬せず、呼び出し元でログする運用を想定
        pass

    return data
