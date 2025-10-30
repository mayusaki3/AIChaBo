# common/chat/chat_loop.py より抜粋
from typing import Any, Dict
from common.session.user_session_manager import user_session_manager as USM
from common.session.server_session_manager import server_session_manager as SSM
from common.secret.store import store
from common.utils.redact import redact
from common.utils.logger import log_warn, log_error

def _extract_chat_policy_from_sessions(user_id: int | None, guild_id: int | None) -> Dict[str, Any]:
    """
    ユーザー/サーバーの非機密セッションからチャット方針（provider/model/その他パラメータ）を合成して返す。
    - ユーザー側 > サーバー側 の優先でマージ
    """
    user_policy = {}
    server_policy = {}

    if guild_id:
        # サーバーの全オプション（dict[str,bool] ではなく、方針が入る想定の場所から取得）
        # 実装側で「どこに非機密を置くか」を決めているはずなので、既存の参照箇所に合わせる
        server_policy = SSM.get_all_non_secret_policy(guild_id) if hasattr(SSM, "get_all_non_secret_policy") else {}
    if user_id:
        user_policy = USM.get_all_non_secret_policy(user_id) if hasattr(USM, "get_all_non_secret_policy") else {}

    # ユーザー優先で上書き
    policy = dict(server_policy)
    policy.update(user_policy)
    return policy

def _resolve_api_key(user_id: int | None, guild_id: int | None, provider: str) -> str | None:
    """
    APIキー解決（ユーザー鍵 → サーバー共有鍵の順）。
    """
    # ユーザー鍵
    if user_id is not None:
        uk = store.get_user_key(user_id, provider)
        if uk:
            return uk
    # サーバー共有鍵
    if guild_id is not None:
        sk = store.get_server_key(guild_id, provider)
        if sk:
            return sk
    return None

def _get_provider_chat_fn(provider: str):
    """
    プロバイダ別のチャット関数を取得。
    ここでは 'ai.{provider}.{provider}_api' のモジュールにある
    call_{provider}_chat(context_list, api_key, model=..., **extra) を探す。
    """
    import importlib
    modname = f"ai.{provider}.{provider}_api"
    mod = importlib.import_module(modname)
    preferred = (f"call_{provider}_chat",)
    for fname in preferred:
        fn = getattr(mod, fname, None)
        if callable(fn):
            return fn
    raise RuntimeError(f"No chat entrypoint found in {modname}. Tried: {', '.join(preferred)}")

async def run(provider: str,
              context_list: list[str],
              user_id: int,
              guild_id: int,
              model: str | None = None) -> str:
    """
    1回分のテキストチャット実行（本番・テスト共通エントリポイント）。
    - 引数は本番呼び出しに合わせて固定（位置引数で呼ぶ前提）。
    - 失敗時は簡潔なエラー文を返す（詳細はログへ）。
    """
    try:
        # 0) 入力検証（最低限）
        if not isinstance(provider, str) or not provider.strip():
            return "（プロバイダが不正です）"
        if not isinstance(context_list, list) or not context_list or not any(isinstance(x, str) and x.strip() for x in context_list):
            return "（入力が空です）"

        # 1) 非機密の“方針”を取得し、必要に応じて model を上書き
        policy = _extract_chat_policy_from_sessions(user_id=user_id, guild_id=guild_id)
        # 方針に provider がある場合でも、引数 provider を優先（呼び元が明示指定）
        # model は明示引数が None のとき、方針から補完
        final_model = model or policy.get("model")
        if not final_model:
            return "（モデル設定が見つかりません。/ac_auth で設定してください）"

        # 2) APIキー解決（ユーザー → サーバー共有）
        api_key = _resolve_api_key(user_id=user_id, guild_id=guild_id, provider=provider)
        if not api_key:
            log_warn(f"[chat_loop] api_key not found: provider={provider}, user={user_id}, guild={guild_id}")
            return "（APIキーが未設定です。/ac_auth で登録してください）"

        # 3) 実行関数を取得
        chat_fn = _get_provider_chat_fn(provider)

        # 4) 追加パラメータ（温度など）は policy から抽出（provider/model は除外）
        extra = {k: v for k, v in policy.items() if k not in ("provider", "model")}

        # 5) 実行
        reply = await chat_fn(context_list=context_list, api_key=api_key, model=final_model, **extra)
        if not isinstance(reply, str):
            reply = str(reply)
        return reply or "（応答が空でした）"

    except Exception as e:
        log_error(f"[chat_loop] failed: {redact(e)}")
        return "（チャット実行でエラーが発生しました）"
