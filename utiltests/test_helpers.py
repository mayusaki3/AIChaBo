# utiltests/test_helpers.py
# -----------------------------------------------------------------------------
# テスト専用ヘルパー（コメント付き差し替え版）
# - Discord を介さず chat_loop をユニットテストするための最小ダミー文脈を生成
# - 本番コードを変更せずにテストを通すため、モデル名などの「非機密の既定値」をここで注入
# - 将来プロバイダを追加する場合は DEFAULT_MODELS に追記するだけでテストが継続可能
# -----------------------------------------------------------------------------

from __future__ import annotations

from typing import Dict, Any

# プロバイダ別の既定モデル（テスト用・非機密）
# 本番の /ac_auth で設定されるモデルと独立。あくまで「テストが最短経路で通る」ための既定値。
DEFAULT_MODELS: Dict[str, str] = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-3-5-sonnet-latest",
    "google": "gemini-1.5-pro",
}


def build_min_context_for_test(provider: str) -> Dict[str, Any]:
    """
    指定プロバイダ向けの最小コンテキストを構築して返す。

    chat_loop 側のモデル解決ロジックは実装差異があり得るため、以下の“保険”を同梱する：
      1) "model" 直指定
      2) "preferred_models" のプロバイダ→モデル対応
      3) "provider_defaults" の階層化既定
    いずれかを参照してもテストが通るようにして、本番コードへの変更を不要化する。
    """
    model = DEFAULT_MODELS.get(provider, "gpt-4o-mini")

    # Discord依存を避けるため、IDはダミー固定値
    # - server_id / user_id / channel_id / thread_id は chat_loop が参照する想定キー
    ctx: Dict[str, Any] = {
        "provider": provider,
        "server_id": 222,
        "user_id": 111,
        "channel_id": 333,
        "thread_id": 444,

        # === モデル解決の“保険”キー群 ===
        "model": model,  # 1) 直指定
        "preferred_models": {provider: model},  # 2) マップ型
        "provider_defaults": {provider: {"model": model}},  # 3) 階層化既定
    }
    return ctx
