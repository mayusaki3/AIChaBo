# -*- coding: utf-8 -*-
"""
common.chat.sharing

チャットセッションの「共有・エクスポート／インポート」ユーティリティ。

主な役割:
- export_session(session):
    内部セッション(dict)から、共有可能な最小限の情報だけを抜き出し、
    JSON文字列としてエクスポートする（バージョンや provider/model を含む）。
- import_session(raw):
    export_session で作られた JSON 文字列を読み込み、
    現行バージョン用のセッション dict に変換・サニタイズする。
- share_to_guild(guild_id, session):
    ギルド単位での共有を行うためのラッパー。
    実際の送信処理は _share_to_server_impl に委譲し、テストから patch 可能にする。
"""

from __future__ import annotations

from typing import Any, Dict, Optional
import json

from common.utils import logger  # type: ignore[import]

# 共有フォーマットのバージョン
_SHARE_VERSION = 1

# デフォルトのプロバイダ / モデル
_DEFAULT_PROVIDER = "openai"
_DEFAULT_MODEL = "gpt-4o"


def _normalize_model(model: Any) -> str:
    """
    モデル名をサニタイズするヘルパー。

    - 文字列でない場合はデフォルトモデルにフォールバック
    - 「*-mini」のようなサフィックスが付いている場合はベース名に丸める
      （例: "gpt-4o-mini" -> "gpt-4o"）

    Args:
        model: 任意型のモデル名

    Returns:
        サニタイズ済みモデル名
    """
    if not isinstance(model, str) or not model:
        return _DEFAULT_MODEL

    # 例: "gpt-4o-mini" -> "gpt-4o"
    if model.endswith("-mini"):
        return model[: -len("-mini")]

    return model


def _sanitize_export_session(session: Dict[str, Any]) -> Dict[str, Any]:
    """
    export_session 用に、共有フォーマットへ詰め替える。

    - version は _SHARE_VERSION を強制
    - id / ts / messages / provider / model を抽出
    - provider / model が無ければデフォルトを補う

    Args:
        session: 内部セッション(dict)

    Returns:
        共有用セッション(dict)
    """
    messages = session.get("messages")
    if not isinstance(messages, list):
        messages = []

    out: Dict[str, Any] = {
        "version": _SHARE_VERSION,
        "id": session.get("id"),
        "ts": session.get("ts"),
        "messages": messages,
    }

    provider = session.get("provider") or _DEFAULT_PROVIDER
    out["provider"] = str(provider)

    model = _normalize_model(session.get("model"))
    out["model"] = model

    return out


def export_session(session: Any) -> str:
    """
    セッションを共有用 JSON 文字列としてエクスポートする。

    - dict 以外が渡された場合は空セッションとして扱う
    - _sanitize_export_session() で必要なフィールドだけを抽出・サニタイズ
    - json.dumps() で文字列化

    Args:
        session: 内部セッション(dict 想定)

    Returns:
        共有用 JSON 文字列
    """
    if not isinstance(session, dict):
        session = {}

    safe = _sanitize_export_session(session)
    return json.dumps(safe, ensure_ascii=False)


def _sanitize_import_session(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    import_session 用に、読み込んだ dict を現行フォーマットへ正規化する。

    - version は常に _SHARE_VERSION に揃える
    - id / ts / messages / provider / model を取り出す
    - messages が list でない場合は空 list
    - provider / model の欠落・不正値はデフォルト補完
    - 古い version / 未指定 version もここで一括処理する

    Args:
        raw: JSON から読み込んだ dict

    Returns:
        内部で扱いやすいセッション dict
    """
    messages = raw.get("messages")
    if not isinstance(messages, list):
        messages = []

    provider = raw.get("provider") or _DEFAULT_PROVIDER
    model = _normalize_model(raw.get("model"))

    normalized: Dict[str, Any] = {
        "version": _SHARE_VERSION,
        "id": raw.get("id"),
        "ts": raw.get("ts"),
        "messages": messages,
        "provider": str(provider),
        "model": model,
    }

    return normalized


def import_session(data: str) -> Optional[Dict[str, Any]]:
    """
    共有セッション JSON 文字列をサニタイズした dict に復元する。

    - 正常系: センシティブ情報を除去した dict を返す
    - JSON 不正: ログに warning を出しつつ None を返す
    - 旧形式 (version 無し / 0 / v=0 等) も互換として受け入れる
    - 不明な将来バージョンは None を返す
    """
    if not isinstance(data, str):
        return None

    try:
        obj = json.loads(data)
    except Exception:
        # logger.get_logger が無い環境でも落ちないように best-effort でログ
        try:
            # 共通ロガー取得（あれば）
            get_logger = getattr(logger, "get_logger", None)
            if callable(get_logger):
                get_logger(__name__).warning("sharing.import_session: invalid JSON")
            else:
                # 旧実装: logger._logger を直接持っている場合
                base_logger = getattr(logger, "_logger", None)
                if base_logger is not None:
                    base_logger.warning("sharing.import_session: invalid JSON")
        except Exception:
            # ログでさらに落ちることは避ける
            pass
        return None

    if not isinstance(obj, dict):
        return None

    # ----- バージョン互換処理 -----
    # 現行: obj["version"] == 1
    # 旧形式想定:
    #   - "version" が無い
    #   - "version" が 0
    #   - "v" だけがある (0/1)
    version = obj.get("version", None)

    # "v" を version として許容（旧データ想定）
    if version is None and "v" in obj:
        version = obj.get("v")

    # 互換として受け入れるバージョン
    #   None … 完全旧形式（version 指定なし）
    #   0    … 旧形式
    #   1    … 現行形式
    if version not in (None, 0, 1):
        # 不明な将来バージョンは読み込み失敗扱い
        return None

    # 正規化として、内部的には 1 にそろえておく（テストでは provider/model などを見る想定）
    obj["version"] = 1

    # サニタイズして返却（export/import/サニタイズ/互換テストで共通利用）
    return _sanitize_session(obj)


def _share_to_server_impl(*, guild_id: int, session: Dict[str, Any], scope: str) -> None:
    """
    実際の「サーバー（ギルド等）への共有」処理。

    テストから patch 対象になる想定のため、実装は薄くしておく。
    実運用では、ここで Discord メッセージ送信や、他プロセスへの連携を行う。

    Args:
        guild_id: 共有先ギルド ID
        session: 共有したいセッション dict
        scope:   共有スコープ（"guild" など）
    """
    log = logger.get_logger(__name__)
    log.info("sharing._share_to_server_impl: scope=%s guild_id=%s", scope, guild_id)
    # ここでは実処理は行わず、ログのみ（テストでは patch で差し替え）


def share_to_guild(*, guild_id: int, session: Dict[str, Any]) -> None:
    """
    ギルド単位でセッションを共有するためのヘルパー。

    - テストでは _share_to_server_impl を patch し、
      guild_id / session / scope="guild" の渡し方を検証している。

    Args:
        guild_id: 共有先ギルド ID
        session: 共有したいセッション dict
    """
    if not isinstance(session, dict):
        # 想定外入力でも落とさず、空セッションとして扱う
        session = {}

    _share_to_server_impl(guild_id=guild_id, session=session, scope="guild")
