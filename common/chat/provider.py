# common/chat/provider.py
# ------------------------------------------------------------
# プロバイダ名の正規化と表示名の提供を一元化するユーティリティ。
# - 内部キー：すべて小文字（secret store / 比較 / 永続化で使用）
# - 表示名  ：ユーザー向けに整形（UIでのみ使用）
# ------------------------------------------------------------
from __future__ import annotations

# 既知プロバイダの表示名マップ（ここに追加すれば UI 表示が揃う）
_DISPLAY_MAP = {
    "openai": "OpenAI",
    "claude": "Claude",
    "anthropic": "Claude",   # 別名が来ても UI は Claude 統一
    "gemini": "Gemini",
    "google": "Gemini",      # 別名が来ても UI は Gemini 統一
}

# 既知プロバイダの同義語 → 正規化キー
_CANONICAL_MAP = {
    "openai": "openai",
    "OpenAI": "openai",
    "gpt": "openai",
    "claude": "claude",
    "anthropic": "claude",
    "Anthropic": "claude",
    "gemini": "gemini",
    "google": "gemini",
    "Google": "gemini",
}

def normalize_provider(name: str) -> str:
    """
    任意の provider 名を小文字の正規化キーに変換する。
    未知の値は lower() を返す（将来の拡張を阻害しない）。
    """
    if not isinstance(name, str) or not name.strip():
        return ""
    return _CANONICAL_MAP.get(name.strip(), name.strip().lower())

def display_provider(canonical: str) -> str:
    """
    小文字の正規化キーをユーザー向けの表示名に変換する。
    未知の値は、そのまま（capitalize程度しない：誤誘導回避）。
    """
    if not canonical:
        return ""
    return _DISPLAY_MAP.get(canonical, canonical)
