"""
M01:T01-03 SecretStore init & errors

SecretStore 初期化と内部ユーティリティの異常系・復旧挙動を検証する。
- ENV優先 / master.key 生成
- _load_json のファイル有無と壊れデータ処理
- 初期ロード時の壊れトークンスキップ
- get_server_key の unknown provider
- _save_json の tmp ファイルクリーンアップ
"""

import json
import os
import stat
import tempfile
from pathlib import Path
from unittest.mock import patch

from common.secret import store as store_mod
from tests._report import run_unittest_suite


ENV_MASTER = "AICHABO_MASTER_KEY"
# 実際の環境変数名は store.py 実装に合わせて調整すること。


class Env:
    """
    SecretStore 初期化テスト用の隔離環境。
    """

    def __init__(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="ss-init-"))
        self.users = self.tmp / "users.json"
        self.servers = self.tmp / "servers.json"
        self.master = self.tmp / "master.key"
        self._orig_env = {}

    def __enter__(self):
        self._orig_env[ENV_MASTER] = os.environ.get(ENV_MASTER)
        return self

    def __exit__(self, exc_type, exc, tb):
        # env 復元
        if self._orig_env.get(ENV_MASTER) is None:
            os.environ.pop(ENV_MASTER, None)
        else:
            os.environ[ENV_MASTER] = self._orig_env[ENV_MASTER]

        # ファイル削除
        for p in [self.users, self.servers, self.master]:
            try:
                if p.exists():
                    p.unlink()
            except OSError:
                pass
        try:
            self.tmp.rmdir()
        except OSError:
            pass

    def new_store(self) -> store_mod.SecretStore:
        return store_mod.SecretStore(
            users_path=self.users,
            servers_path=self.servers,
            masterkey_path=self.master,
        )


# --- テスト関数 -----------------------------------------------------------


def test_01_init_with_env_key_no_master_file() -> None:
    """
    ENV にキーがある場合:
    - master.key ファイルは生成されないこと。
    """
    with Env() as env:
        os.environ[ENV_MASTER] = "A" * 44  # 32 bytes base64 相当のダミー値に要調整
        ss = env.new_store()
        assert isinstance(ss, store_mod.SecretStore)
        assert not env.master.exists()


def test_02_init_without_env_generates_masterkey_and_handles_chmod_error() -> None:
    """
    ENV が無い場合:
    - master.key を生成すること。
    - chmod 失敗時も例外を飲み込むこと。
    """
    with Env() as env:
        os.environ.pop(ENV_MASTER, None)

        # chmod で例外を発生させる
        with patch.object(os, "chmod", side_effect=OSError("denied")):
            ss = env.new_store()
        assert isinstance(ss, store_mod.SecretStore)
        assert env.master.exists()


def test_03_load_json_when_path_not_exists_returns_empty_dict() -> None:
    """
    _load_json:
    - ファイルが存在しない場合 {} を返すこと。
    """
    with Env() as env:
        # new_store() 内部で _load_json が呼ばれる前提
        ss = env.new_store()
        assert ss.get_user_keys(1) == {}
        assert ss.get_server_keys(1) == {}


def test_04_corrupted_cipher_is_skipped_for_user_tokens() -> None:
    """
    起動時に users.json 内の壊れたトークンは読み飛ばされること。
    """
    with Env() as env:
        # 正常と壊れ値を混在させる
        data = {
            "1": {
                "openai": "invalid-cipher",  # 壊れ
                "gemini": store_mod._enc(b"OK", b"0" * 32).decode("ascii"),
            }
        }
        env.users.write_text(json.dumps(data), encoding="utf-8")

        ss = env.new_store()
        # 壊れ値は無視され、正常分だけ残る想定
        keys = ss.get_user_keys(1)
        assert keys.get("gemini") == b"OK"


def test_05_server_keys_skip_only_corrupt_entries() -> None:
    """
    起動時に servers.json 内の壊れたトークンのみスキップされること。
    """
    with Env() as env:
        data = {
            "777": {
                "openai": store_mod._enc(b"OK", b"0" * 32).decode("ascii"),
                "ng": "invalid-cipher",
            }
        }
        env.servers.write_text(json.dumps(data), encoding="utf-8")

        ss = env.new_store()
        assert ss.get_server_keys(777) == {"openai": b"OK"}


def test_06_get_server_key_unknown_provider_returns_none() -> None:
    """
    get_server_key:
    - 未知 provider 名は None を返すこと。
    """
    with Env() as env:
        ss = env.new_store()
        assert ss.get_server_key(1, "nope") is None


def test_07_save_json_tmp_cleanup_on_error() -> None:
    """
    _save_json:
    - 書き込み失敗時でも tmp ファイルがクリーンアップされること。
    - ここでは json.dump 相当をモックして強制失敗させる。
    """
    with Env() as env:
        ss = env.new_store()

        # _save_json 内部で利用される json.dump / open をモック
        # 実装に応じて調整。ここでは dump 時に例外を投げさせる想定。
        def boom(*args, **kwargs):
            raise TypeError("boom")

        target = "common.secret.store.json_dump" if hasattr(store_mod, "json_dump") else "json.dump"
        with patch(target, side_effect=boom):
            try:
                ss._save_json(env.users, {"x": 1})
            except TypeError:
                pass

        # tmp ファイルが残っていないことのみ確認
        tmp_candidates = list(env.tmp.glob("*.tmp"))
        assert tmp_candidates == []


# --- mapping / エントリポイント -------------------------------------------

mapping = {
    "test_01_init_with_env_key_no_master_file":
        ("M01:T01-03-01", "env優先: master.key未生成"),
    "test_02_init_without_env_generates_masterkey_and_handles_chmod_error":
        ("M01:T01-03-02", "env無し: master.key生成 + chmod例外経路"),
    "test_03_load_json_when_path_not_exists_returns_empty_dict":
        ("M01:T01-03-03", "_load_json: pathなし -> {}"),
    "test_04_corrupted_cipher_is_skipped_for_user_tokens":
        ("M01:T01-03-04", "破損トークン(user)はスキップ"),
    "test_05_server_keys_skip_only_corrupt_entries":
        ("M01:T01-03-05", "破損トークン(server)はスキップ"),
    "test_06_get_server_key_unknown_provider_returns_none":
        ("M01:T01-03-06", "未知provider -> None"),
    "test_07_save_json_tmp_cleanup_on_error":
        ("M01:T01-03-07", "_save_json: 失敗時tmp削除"),
}


if __name__ == "__main__":
    run_unittest_suite("M01:T01-03", mapping, globals())
