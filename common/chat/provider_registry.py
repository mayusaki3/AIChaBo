# common/chat/provider_registry.py
# ------------------------------------------------------------
# Provider Adapter Registry
# 役割:
#   - provider key と chat adapter callable の対応を管理する。
#   - common/chat から ai/{provider} への直接依存を排除するための境界となる。
#
# 注意点:
#   - このモジュールは AI provider API を直接呼び出さない。
#   - このモジュールは API キー等の機密情報を保持しない。
#   - adapter の登録状態はプロセス内メモリのみで管理する。
# ------------------------------------------------------------

from __future__ import annotations

from collections import OrderedDict
from typing import Awaitable, Callable, Dict, List, Protocol, runtime_checkable

from common.chat.provider import normalize_provider


@runtime_checkable
class ChatProviderAdapter(Protocol):
    """
    役割:
      チャット用 AI provider adapter の最小 callable 形を表す。

    注意点:
      初期移行では既存 provider callable 互換を優先し、戻り値は str とする。
      将来的に tool request / continuation / token usage を扱う場合は、構造化 result へ拡張する。

    引数:
      context_list: LLM に渡す会話文脈。
      api_key: 呼び出し時に解決済みの API キー。
      model: 使用モデル名。
      **options: max_tokens などの追加設定。

    戻り値:
      provider から得られたテキスト応答。
    """

    def __call__(
        self,
        context_list: List[str],
        api_key: str,
        model: str,
        **options,
    ) -> Awaitable[str]:
        """チャット応答を非同期に生成する。"""
        ...


# 登録順の安定性を保つため OrderedDict を使用する。
_PROVIDERS: "OrderedDict[str, ChatProviderAdapter]" = OrderedDict()


def _normalize_provider_key(provider: str) -> str:
    """
    役割:
      registry 内部で使用する provider key を正規化する。

    引数:
      provider: 外部から渡された provider 名。

    戻り値:
      正規化済み provider key。

    例外:
      ValueError: provider が空または正規化不能の場合。
    """
    key = normalize_provider(provider)
    if not key:
        raise ValueError("provider is required")
    return key


def register_provider(provider: str, adapter: ChatProviderAdapter, *, overwrite: bool = False) -> None:
    """
    役割:
      provider key に対応する chat adapter callable を登録する。

    注意点:
      - 重複登録は既定では拒否する。
      - テストや reload など明示的な差し替えが必要な場合のみ overwrite=True を使用する。
      - API キー等の機密情報は登録対象に含めない。

    引数:
      provider: provider 名。内部で正規化される。
      adapter: チャット応答を生成する callable。
      overwrite: 既存 provider を上書きするか。

    戻り値:
      なし。

    例外:
      ValueError: provider が空、または重複登録の場合。
      TypeError: adapter が callable でない場合。
    """
    key = _normalize_provider_key(provider)

    if not callable(adapter):
        raise TypeError("adapter must be callable")

    if key in _PROVIDERS and not overwrite:
        raise ValueError(f"provider already registered: {key}")

    _PROVIDERS[key] = adapter


def resolve_provider(provider: str) -> ChatProviderAdapter:
    """
    役割:
      provider key に対応する adapter callable を解決する。

    引数:
      provider: provider 名。内部で正規化される。

    戻り値:
      登録済み ChatProviderAdapter。

    例外:
      ValueError: provider が空または正規化不能の場合。
      KeyError: provider が未登録の場合。
    """
    key = _normalize_provider_key(provider)
    try:
        return _PROVIDERS[key]
    except KeyError:
        raise KeyError(f"provider is not registered: {key}")


def has_provider(provider: str) -> bool:
    """
    役割:
      provider が登録済みかを返す。

    引数:
      provider: provider 名。内部で正規化される。

    戻り値:
      登録済みなら True。provider が空または未登録なら False。
    """
    try:
        key = _normalize_provider_key(provider)
    except ValueError:
        return False
    return key in _PROVIDERS


def list_providers() -> List[str]:
    """
    役割:
      登録済み provider key の一覧を返す。

    戻り値:
      登録順を保持した provider key 一覧。
    """
    return list(_PROVIDERS.keys())


def clear_providers() -> None:
    """
    役割:
      registry を空にする。

    注意点:
      主にテスト初期化、reload 前処理で使用する。
    """
    _PROVIDERS.clear()


def snapshot_providers() -> Dict[str, ChatProviderAdapter]:
    """
    役割:
      現在の registry 状態を退避する。

    戻り値:
      provider key と adapter の対応を保持した shallow copy。
    """
    return dict(_PROVIDERS)


def restore_providers(snapshot: Dict[str, ChatProviderAdapter]) -> None:
    """
    役割:
      snapshot_providers で退避した状態へ registry を復元する。

    注意点:
      snapshot が dict でない場合は安全側として空 registry に復元する。

    引数:
      snapshot: provider key と adapter の対応。

    戻り値:
      なし。
    """
    _PROVIDERS.clear()

    if not isinstance(snapshot, dict):
        return

    for provider, adapter in snapshot.items():
        register_provider(provider, adapter, overwrite=True)
