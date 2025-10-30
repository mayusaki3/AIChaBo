# utiltests/test_helpers.py
# -----------------------------------------------------------------------------
# 目的:
# - .envtest の有無で MOCK/REAL を自動判定し、実行環境バナーを表示
# - テスト実行時は SecretStore の保存先を「テスト専用」に切り替え
# - MOCK の場合はダミー鍵と非機密メタ（モデル名）を USM/Store に投入
# - REAL の場合は .envtest から API キーを読み取り投入（あれば）
# - 後始末: SecretStore に入れた鍵を削除
#
# ポリシー:
# - 本番コード（USM/SSM/Store/chat_loop 等）にテスト専用 API を追加しない
# - 変更は utiltests 側に閉じる（Store の base_dir はテスト内で安全に差し替え）
# -----------------------------------------------------------------------------

from __future__ import annotations

import os
import pathlib
from typing import Dict, Tuple

# 本番のストア/USM を直接利用（テスト時だけ base_dir を差し替える）
from common.secret.store import store as STORE
from common.session.user_session_manager import user_session_manager as USM

# テストで用いる固定 ID（本番とは衝突しないダミー値）
TEST_USER_ID: int = 111
TEST_GUILD_ID: int = 222

# デフォルトのテスト用保存先（リポジトリ内・追跡外の領域）
TEST_STORE_DIR = pathlib.Path("common/secret/test")

# .envtest が無いときは MOCK とする
ENVTEST_PATH = pathlib.Path("utiltests/.envtest")


# -----------------------------------------------------------------------------
# 低レベル: .envtest の軽量ローダ（外部依存を増やさない）
# -----------------------------------------------------------------------------
def _parse_envfile(path: pathlib.Path) -> Dict[str, str]:
    """
    シンプルな KEY=VALUE 形式の .env 互換パーサ（引用・エスケープは簡略）
    行頭 # はコメントとして無視。空行はスキップ。
    """
    env: Dict[str, str] = {}
    if not path.exists():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        env[k] = v
    return env


def load_envtest() -> Dict[str, str]:
    """
    .envtest を読み込んで辞書を返す。
    - .envtest が無い → {"MODE": "MOCK"}
    - .envtest がある → {"MODE": "REAL", 各 API_KEY...}
    """
    env = _parse_envfile(ENVTEST_PATH)
    if env:
        env["MODE"] = "REAL"
    else:
        env = {"MODE": "MOCK"}
    return env


# -----------------------------------------------------------------------------
# 実行環境バナー
# -----------------------------------------------------------------------------
def banner_print_env(env: Dict[str, str]) -> None:
    """
    テスト冒頭に環境情報を人間可読で表示。
    """
    mode = env.get("MODE", "MOCK")
    print("=== AIChaBo chat_loop test ===")
    print(f"Mode     : {mode} ('.envtest' {'found' if ENVTEST_PATH.exists() else 'not found'})")
    print(f".envtest : {ENVTEST_PATH if ENVTEST_PATH.exists() else '(no file)'}")

    base_dir = getattr(STORE, "_base_dir", None)
    if base_dir:
        print(f"StoreDir : {base_dir}")
    else:
        print("StoreDir : (store._base_dir 不明。既定保存先を使用中と想定)")
    print("")


# -----------------------------------------------------------------------------
# SecretStore の保存先をテスト専用に切り替える
# -----------------------------------------------------------------------------
def ensure_test_store_base_dir() -> None:
    """
    SecretStore の保存先をテスト専用ディレクトリに切り替える。
    - 既存の SecretStore 実装に setter が無くても、テスト時のみ _base_dir を上書き。
    - 安全性: テスト時のみ使用し、CI とローカルの隔離に使う。
    """
    TEST_STORE_DIR.mkdir(parents=True, exist_ok=True)
    # 既存の store 実装が _base_dir を持つ前提で差し替え（テスト専用）
    setattr(STORE, "_base_dir", str(TEST_STORE_DIR))


# -----------------------------------------------------------------------------
# 非機密メタの投入（USM）
# -----------------------------------------------------------------------------
def seed_non_secret_meta(provider: str, model: str) -> None:
    """
    USM に「APIキーを含まない認証メタ（provider/model）」を注入する。
    本番でも使う USM の通常 API（set_session）だけで完結させる。
    """
    cur = USM.get_session(TEST_USER_ID) or {}
    auth = cur.get("auth") or {}
    meta = auth.get(provider) or {}

    # 最小限の必須フィールドのみ（それ以外の項目があっても壊さない）
    meta["provider"] = provider
    meta["model"] = model

    auth[provider] = meta
    cur["auth"] = auth
    USM.set_session(TEST_USER_ID, cur)


# -----------------------------------------------------------------------------
# 鍵の投入（SecretStore）
# -----------------------------------------------------------------------------
def seed_secret_keys(provider: str, user_key: str, shared: bool = False) -> None:
    """
    SecretStore にユーザー鍵（必須）と、shared=True の場合はサーバー共有鍵も投入。
    """
    # user key
    STORE.put_user_key(TEST_USER_ID, provider, _to_bytes(user_key))

    # optional: server shared key
    if shared:
        # 共有鍵はユーザー鍵と区別してもよいが、ここではシンプルに同値で投入
        STORE.put_server_key(TEST_GUILD_ID, provider, _to_bytes(user_key))


def cleanup_secret_keys(provider: str) -> None:
    """
    SecretStore に入れたテスト用の鍵を削除（user/server 両方試す）。
    Store 実装差異に吸収的に対応（delete_*_keys / delete_*_key の両形を許容）。
    """
    # user
    if hasattr(STORE, "delete_user_keys"):
        STORE.delete_user_keys(TEST_USER_ID, provider)  # 推奨 API（複数対応）
    elif hasattr(STORE, "delete_user_key"):
        STORE.delete_user_key(TEST_USER_ID, provider)   # 単数 API 互換
    # server
    if hasattr(STORE, "delete_server_keys"):
        STORE.delete_server_keys(TEST_GUILD_ID, provider)
    elif hasattr(STORE, "delete_server_key"):
        STORE.delete_server_key(TEST_GUILD_ID, provider)


# -----------------------------------------------------------------------------
# MOCK 用シード（鍵と非機密メタの両方を投入）
# -----------------------------------------------------------------------------
def seed_mock_for_provider(provider: str, model: str = "mock", shared: bool = False) -> None:
    """
    MOCK 実行用に、指定 provider のダミー鍵と非機密メタを投入。
    - 非機密メタ（USM）: provider/model を注入
    - 秘密鍵（Store）: "sk-mock-<provider>" を投入
    """
    dummy_key = f"sk-mock-{provider}"
    seed_non_secret_meta(provider, model=model)
    seed_secret_keys(provider, dummy_key, shared=shared)


# -----------------------------------------------------------------------------
# .envtest → 鍵の投入（REAL 用）
# -----------------------------------------------------------------------------
def seed_real_keys_from_env(provider: str, env: Dict[str, str], shared: bool = False) -> bool:
    """
    REAL モード時、.envtest から指定 provider の API キーを読み取り Store へ投入。
    戻り値: True=投入した / False=キーが見つからず未投入
    期待キー名:
      - openai:     OPENAI_API_KEY
      - anthropic:  ANTHROPIC_API_KEY
      - google:     GOOGLE_API_KEY
    """
    keymap = {
        "openai":    "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "google":    "GOOGLE_API_KEY",
    }
    var = keymap.get(provider)
    if not var:
        return False
    value = env.get(var)
    if not value:
        return False

    seed_secret_keys(provider, value, shared=shared)
    return True


# -----------------------------------------------------------------------------
# ユーティリティ
# -----------------------------------------------------------------------------
def _to_bytes(s: str | bytes) -> bytes:
    """store._enc は bytes 前提なので、str を bytes に安全変換。"""
    if isinstance(s, bytes):
        return s
    return s.encode("utf-8", errors="strict")


# -----------------------------------------------------------------------------
# エクスポート（テストから import される関数名の一覧）
# -----------------------------------------------------------------------------
__all__ = [
    # 環境判定/表示
    "load_envtest",
    "banner_print_env",
    "ensure_test_store_base_dir",
    # テスト用 ID 定数
    "TEST_USER_ID",
    "TEST_GUILD_ID",
    # シード/クリーンアップ
    "seed_non_secret_meta",
    "seed_secret_keys",
    "seed_mock_for_provider",
    "seed_real_keys_from_env",
    "cleanup_secret_keys",
]
