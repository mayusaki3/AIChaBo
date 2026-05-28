from typing import Any, Dict

from common.session.user_session_manager import user_session_manager as USM
from common.session.server_session_manager import server_session_manager as SSM
from common.secret.store import store
from common.utils.redact import redact
from common.utils.logger import log_warn, log_error
from common.chat import provider_registry


def _extract_chat_policy_from_sessions(
    user_id: int | None,
    guild_id: int | None,
) -> dict:
    """
    USM/SSM から非機密ポリシーを集約してマージする。

    仕様:
      - guild_id があれば SSM の non-secret policy を読み込む
      - user_id があれば USM の non-secret policy を読み込み、同一キーはユーザー側で上書き
      - user_id / guild_id ともに None の場合は空 dict
    前提:
      - SSM / USM はそれぞれ get_all_non_secret_policy(...) を実装している（互換ガード不要）
    """
    merged: dict = {}

    if guild_id is not None:
        server_policy = SSM.get_all_non_secret_policy(guild_id) or {}
        merged.update(server_policy)

    if user_id is not None:
        user_policy = USM.get_all_non_secret_policy(user_id) or {}
        # ユーザー設定でサーバ設定を上書き
        merged.update(user_policy)

    return merged


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
    Provider Adapter Registry から provider adapter callable を取得する。

    注意点:
      - chat_loop は ai.{provider} の配置規約を知らない。
      - chat_loop は call_{provider}_chat の命名規約を知らない。
      - provider adapter の登録責務は bootstrap 側に存在する。
    """
    return provider_registry.resolve_provider(provider)


async def run(
    provider: str,
    context_list: list[str],
    user_id: int,
    guild_id: int,
    model: str | None = None,
) -> str:
    """
    1回分のテキストチャット実行（本番・テスト共通エントリポイント）。

    仕様:
      - Provider Adapter Registry 経由で provider adapter を解決する。
      - API キーは SecretStore から解決する。
      - provider adapter は UI 層へ未処理例外を伝播してはならない。

    引数:
      provider: provider 名。
      context_list: LLM に渡す会話文脈。
      user_id: 実行ユーザー ID。
      guild_id: 実行サーバー ID。
      model: 明示指定モデル。None の場合は policy から補完。

    戻り値:
      チャット応答文字列。
    """
    try:
        # 0) 入力検証（最低限）
        if not isinstance(provider, str) or not provider.strip():
            return "（プロバイダが不正です）"

        if (
            not isinstance(context_list, list)
            or not context_list
            or not any(isinstance(x, str) and x.strip() for x in context_list)
        ):
            return "（入力が空です）"

        # 1) 非機密の“方針”を取得し、必要に応じて model を上書き
        policy = _extract_chat_policy_from_sessions(
            user_id=user_id,
            guild_id=guild_id,
        )

        # model は明示引数が None のとき、方針から補完
        final_model = model or policy.get("model")
        if not final_model:
            return "（モデル設定が見つかりません。/ac_auth で設定してください）"

        # 2) APIキー解決（ユーザー → サーバー共有）
        api_key = _resolve_api_key(
            user_id=user_id,
            guild_id=guild_id,
            provider=provider,
        )

        if not api_key:
            log_warn(
                f"[chat_loop] api_key not found: provider={provider}, user={user_id}, guild={guild_id}"
            )
            return "（APIキーが未設定です。/ac_auth で登録してください）"

        # 3) provider adapter を registry から取得
        chat_fn = _get_provider_chat_fn(provider)

        # 4) provider callable へ渡す追加パラメータを抽出
        #    初期移行では provider callable 互換性を優先し、
        #    provider/model を除外した policy のみを渡す。
        extra = {
            k: v
            for k, v in policy.items()
            if k not in ("provider", "model")
        }

        # 5) provider adapter 実行
        reply = await chat_fn(
            context_list=context_list,
            api_key=api_key,
            model=final_model,
            **extra,
        )

        if not isinstance(reply, str):
            reply = str(reply)

        return reply or "（応答が空でした）"

    except Exception as e:
        log_error(f"[chat_loop] failed: {redact(e)}")
        return "（チャット実行でエラーが発生しました）"
