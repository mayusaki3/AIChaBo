# common/chat/auth.py
# ------------------------------------------------------------
# LLM呼び出し用の“非機密設定 + 機密APIキー”の解決ユーティリティ。
# - 非機密（provider/model/max_tokens 等）は UserSessionManager > ServerSessionManager の順に採用
# - 機密APIキーは SecretStore から取得（ユーザー > サーバーの順）
# - provider 名は SecretStore のキー規約に合わせて小文字正規化
# ------------------------------------------------------------
from __future__ import annotations
from typing import Optional, Dict, Any

from common.session.user_session_manager import user_session_manager as USM
from common.session.server_session_manager import server_session_manager as SSM
from common.secret.store import store
from common.chat.provider import normalize_provider

def resolve_auth_and_key(
    guild_id: Optional[int],
    user_id: Optional[int],
) -> Dict[str, Any]:
    """
    LLMチャット呼び出し用の設定を統合して返す。

    優先順位:
      1) ユーザー単位の非機密設定（USM.get_session(user_id)）
      2) サーバー共有の非機密設定（SSM.get_shared_auth_config(guild_id)）
      3) APIキーは SecretStore で ユーザー > サーバー の順で探索
         - provider 名は小文字化して SecretStore キーに合わせる
         - ユーザーになければサーバーを参照

    Returns:
        {
          "provider": "OpenAI",
          "model": "gpt-4o-mini",
          "api_key": "xxxxxxxx",
          "max_tokens": 2048,
          ...
        }
        ※ 不足がある場合は {} を返す
    """
    # 非機密（provider/model 等）
    auth = (USM.get_session(user_id) if user_id else None) or \
           (SSM.get_shared_auth_config(guild_id) if guild_id else None) or {}
    chat = dict(auth.get("chat") or {})

    provider = normalize_provider((chat.get("provider") or "").strip())
    model    = (chat.get("model") or "").strip()
    if not provider or not model:
        return {}  # 必須情報不足

    # 機密（APIキー）
    prov_key = provider.lower()  # SecretStore 規約に合わせる
    api_bytes = None
    if user_id:
        api_bytes = store.get_user_key(user_id, prov_key)
    if (not api_bytes) and guild_id:
        api_bytes = store.get_server_keys(guild_id).get(prov_key)

    if not api_bytes:
        return {}  # APIキー未登録

    # 返却オブジェクト整形（既存値を温存しつつ最低限を保証）
    chat["provider"]   = provider  # 小文字正規化で返す（表示は呼び出し側で display_provider へ）
    chat["model"]      = model
    chat["api_key"]    = api_bytes.decode("utf-8", errors="ignore")
    chat["max_tokens"] = chat.get("max_tokens", 2048)
    return chat
