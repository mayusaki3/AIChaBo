# ai/provider_bootstrap.py
# ------------------------------------------------------------
# Provider Bootstrap
# 役割:
#   - 標準 AI provider adapter を Provider Adapter Registry へ登録する。
#   - common/chat から AI provider 実装への直接依存を排除する。
#
# 注意点:
#   - bootstrap は API キーを扱わない。
#   - bootstrap は外部 AI API を呼び出さない。
#   - bootstrap は adapter callable を registry に登録するだけである。
# ------------------------------------------------------------

from __future__ import annotations

from common.chat import provider_registry as registry

# 既存 provider callable を adapter として再利用する。
from ai.openai.openai_api import call_openai_chat
from ai.gemini.gemini_api import call_gemini_chat
from ai.claude.claude_api import call_claude_chat


# 標準 provider の登録順序を固定する。
_STANDARD_PROVIDERS = [
    ("openai", call_openai_chat),
    ("gemini", call_gemini_chat),
    ("claude", call_claude_chat),
]


def get_standard_provider_keys() -> list[str]:
    """
    役割:
      標準 provider key 一覧を固定順で返す。

    戻り値:
      登録対象 provider key 一覧。
    """
    return [provider for provider, _adapter in _STANDARD_PROVIDERS]


def register_standard_providers(overwrite: bool = False) -> None:
    """
    役割:
      標準 provider adapter を registry に登録する。

    注意点:
      - API キーは不要。
      - 外部 API 呼び出しは行わない。
      - provider callable の import は bootstrap 層に閉じ込める。

    引数:
      overwrite: 既存 provider を上書きするか。

    戻り値:
      なし。

    例外:
      ValueError:
        overwrite=False かつ provider が既登録の場合。
      TypeError:
        adapter callable が不正な場合。
    """
    for provider, adapter in _STANDARD_PROVIDERS:
        registry.register_provider(provider, adapter, overwrite=overwrite)


def reload_standard_providers() -> None:
    """
    役割:
      registry を標準 provider 構成へ再構成する。

    処理手順:
      1. 現在の registry 状態を snapshot する
      2. registry を clear する
      3. 標準 provider を再登録する
      4. provider 一覧を検証する
      5. 失敗時は snapshot へ復元する

    戻り値:
      なし。

    例外:
      RuntimeError:
        reload 後の provider 検証に失敗した場合。
      Exception:
        provider 登録処理失敗時は呼び出し元へ再送出する。
    """
    snapshot = registry.snapshot_providers()

    try:
        registry.clear_providers()
        register_standard_providers(overwrite=True)

        actual = registry.list_providers()
        expected = get_standard_provider_keys()

        if actual != expected:
            raise RuntimeError(
                f"provider reload verification failed: expected={expected}, actual={actual}"
            )

    except Exception:
        registry.restore_providers(snapshot)
        raise
