# common/chat/chat_loop.py
# -*- coding: utf-8 -*-
"""
chat_loop.py
----------------------------------------------------------------------
プラットフォーム非依存の「チャット1往復」を担当する最小実装。

【役割】
- コンテキスト（non_secret_auth = 非機密の“方針”、例：provider/model）を受け取り
- SecretStore から API キーを解決（ユーザー鍵 → サーバー共有鍵の順でフォールバック）
- プロバイダ別ラッパ（OpenAI / Claude / Gemini）を呼び出し
- 返答テキストを返す

【前提】
- APIキーは common/secret/store.py の SecretStore に保存済み
- 非機密の “どのプロバイダ・モデルを使うか” は context["non_secret_auth"]["chat"] に格納
- provider名は normalize_provider() で正規化（"OpenAI"/"openai" 等の表記揺れを吸収）

【依存しないもの】
- Discord の2000文字制限や typing 表示は UI 層で実装（ここでは扱わない）

【将来拡張ポイント（型だけコメントで示す）】
- 複数プロバイダのフォールバック
- システム/ユーザー/開発プロンプトの組み立て（ここでは user_text をそのまま渡す）
- 画像・ツールコール等の分岐
- 応答キャッシュ
"""

from __future__ import annotations

from typing import Any, Dict, Optional
import importlib

# --- 共通ユーティリティ／管理 ---
from common.utils.redact import redact
try:
    from common.utils.logger import log_info, log_warn, log_error  # 任意（存在しなくても致命ではない）
except Exception:
    def log_info(msg: str):  # フォールバック
        print(msg)
    def log_warn(msg: str):
        print(msg)
    def log_error(msg: str):
        print(msg)

from common.chat.provider import normalize_provider  # provider名の正規化
from common.secret.store import store  # SecretStore シングルトン
from common.session.user_session_manager import user_session_manager as USM
from common.session.server_session_manager import server_session_manager as SSM


# --- プロバイダ呼び出しの薄いラッパ（既存 ai/* ラッパを呼ぶ） -----------------
def _get_provider_chat_fn(provider: str):
    """
    各プロバイダの“チャット入口関数”を動的に解決する。
    候補名のいずれかが見つかれば採用（既存実装名を壊さない）。
    期待IF: async def <entry>(context_list:list[str], api_key:str, model:str, **kwargs) -> str
    ※テキスト専用。Vision/画像生成（analyze_*/generate_*）は扱わない。
    """
    p = normalize_provider(provider)
    modmap = {
        "openai":    "ai.openai.openai_api",
        "anthropic": "ai.claude.claude_api",
        "google":    "ai.gemini.gemini_api",
    }
    modname = modmap.get(p)
    if not modname:
        raise RuntimeError(f"Unsupported provider: {provider}")
    mod = importlib.import_module(modname)

    # テキスト専用のAPI名のみ
    preferred = ("call_openai_chat", "call_claude_chat", "call_gemini_chat")
    for fname in preferred:
        fn = getattr(mod, fname, None)
        if callable(fn):
            return fn

    raise AttributeError(
        f"No chat entrypoint found in {modname}. "
        "Set __CHAT_ENTRYPOINT__='function_name' in that module or expose one of the known names."
    )

# --- APIキー解決 -------------------------------------------------------------
def _resolve_api_key(
    user_id: Optional[int],
    guild_id: Optional[int],
    provider: str,
) -> Optional[str]:
    """
    APIキーを SecretStore から解決する。
    優先度：ユーザー鍵 → サーバー共有鍵 → なし
    """
    prov = normalize_provider(provider)

    # 1) ユーザー鍵
    if user_id is not None:
        key = store.get_user_key(user_id=int(user_id), provider=prov)
        if key:
            return key.decode("utf-8", "ignore") if isinstance(key, (bytes, bytearray)) else str(key)

    # 2) サーバー共有鍵
    if guild_id is not None:
        key = store.get_server_key(guild_id=int(guild_id), provider=prov)
        if key:
            return key.decode("utf-8", "ignore") if isinstance(key, (bytes, bytearray)) else str(key)

    # 3) 見つからない
    return None

# --- モデル・追加パラメータの抽出 --------------------------------------------
def _extract_chat_policy(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    context["non_secret_auth"]["chat"] から provider / model / 追加パラメータを引き出す。
    見つからなければ空を返す（上位でバリデーション）。
    """
    ns = (context or {}).get("non_secret_auth") or {}
    chat_cfg = ns.get("chat") or {}
    # ここでは provider / model が最低限必要。他は kwargs としてそのまま通す。
    return dict(chat_cfg)

# --- 本体：1往復 -------------------------------------------------------------
async def run(user_text: str, context: Dict[str, Any]) -> str:
    """
    1回分のチャット実行。
    失敗時は簡潔なエラー文を返す（詳細はログに残す）。
    """
    try:
        # 0) 入力検証（最低限）
        if not isinstance(user_text, str) or not user_text.strip():
            return "（入力が空です）"

        # 1) 非機密の“方針”を取得（provider/model 等）
        policy = _extract_chat_policy(context)
        provider = policy.get("provider")
        model = policy.get("model")
        if not provider or not model:
            return "（モデル設定が見つかりません。/ac_auth で設定してください）"

        # 2) APIキー解決（ユーザー → サーバー共有の順）
        user_id = context.get("user_id")
        guild_id = context.get("guild_id")
        api_key = _resolve_api_key(user_id=user_id, guild_id=guild_id, provider=provider)
        if not api_key:
            # 共有鍵も含め存在しない
            # - ユーザー視点では「鍵が未設定」のみを伝える（詳細はログへ）
            log_warn(f"[chat_loop] api_key not found: provider={provider}, user={user_id}, guild={guild_id}")
            return "（APIキーが未設定です。/ac_auth で登録してください）"

        # 3) 実行関数を取得
        chat_fn = _get_provider_chat_fn(provider)

        # 4) 追加パラメータ（温度など）は policy からそのまま渡す（model/provider は個別で渡すため除外）
        extra = {k: v for k, v in policy.items() if k not in ("provider", "model")}

        # 5) 実行
        reply = await chat_fn(context_list=[user_text], api_key=api_key, model=model, **extra)
        if not isinstance(reply, str):
            # ラッパ実装が dict を返した場合などは防御的に文字列化
            reply = str(reply)

        return reply or "（応答が空でした）"

    except Exception as e:
        # 失敗時は要約メッセージ＋ログ（鍵は redact で隠す）
        log_error(f"[chat_loop] failed: {redact(e)}")
        return "（チャット実行でエラーが発生しました）"
