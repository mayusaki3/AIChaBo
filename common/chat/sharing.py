# common/chat/sharing.py
# ------------------------------------------------------------
# 認証情報のサーバー共有操作（判定 / 共有 / 共有解除）を一元化。
# - SecretStore は「鍵（機密）」のみを保持
# - 非機密（provider/model 等）は ServerSessionManager / UserSessionManager が保持
# - 原子性：単純コピーのためファイルロックまでの厳密性は要求しないが、
#            例外時は部分書き込みを避けるため、プロバイダ単位で完了確認を行う
# ------------------------------------------------------------
from __future__ import annotations

from typing import Dict
from common.secret.store import store
from common.session.user_session_manager import user_session_manager as USM
from common.session.server_session_manager import server_session_manager as SSM
from common.chat.provider import normalize_provider

def is_already_shared(guild_id: int) -> bool:
    """サーバーに1つでも共有鍵があれば True."""
    keys = store.get_server_keys(guild_id)
    return bool(keys)

def share_user_auth_to_server(guild_id: int, user_id: int) -> Dict[str, bool]:
    """
    ユーザーの登録済み「全プロバイダ鍵」をサーバーへコピー。
    戻り値： { canonical_provider: True/False }（コピーできたかの結果）
    """
    # ユーザー鍵（機密）とユーザー非機密の突合
    # 1) SecretStore（機密）……鍵を列挙
    # 2) USM（非機密）……… 利用中プロバイダのヒント（なくてもよい）
    user_cfg = USM.get_session(user_id) or {}
    chat = user_cfg.get("chat") or {}
    hint_provider = normalize_provider(chat.get("provider", ""))

    # SecretStore からユーザーの全プロバイダ鍵を収集
    results: Dict[str, bool] = {}
    # まずは hint（使用中プロバイダ）を優先的にコピー
    ordered = []
    if hint_provider:
        ordered.append(hint_provider)
    # 他のプロバイダ（重複除去）
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
            results[prov] = False

    # 非機密の共有状態（SSM）も同期（プロバイダ/モデルなど）
    # 共有ON/OFFフラグを持たない方針のため、ここでは SSM には“内容”のみ反映。
    # ※ ac_authsharing 側でメッセージ表示用に使う。
    if chat:
        SSM.set_shared_auth_config(guild_id, {"chat": chat})

    return results

def unshare_server_auth(guild_id: int) -> bool:
    """
    サーバー共有鍵（機密）を全削除する。
    非機密は SSM 側に残す（/ac_removeauth の方針と整合）。
    """
    try:
        # 既存のすべてのプロバイダ鍵を削除
        for prov in list(store.get_server_keys(guild_id).keys()):
            store.delete_server_key(guild_id, prov)
        return True
    except Exception:
        return False
