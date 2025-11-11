"""
M01:T01-02 SecretStore edges & recovery

SecretStore の周辺挙動と復旧系を集中的に検証するスイート。
方針:
- すべて「関数 + mapping + run_unittest_suite」スタイルで実装。
- 各テストは一時ディレクトリ配下に users.json / servers.json を生成し、
  SecretStore をそのパスで初期化して検証する。
- 旧テスト (〜_old) と同等の意味を持つケースのみを残す。
"""

import json
import os
import tempfile
from pathlib import Path

from common.secret.store import SecretStore
from tests._report import run_unittest_suite


# --- 共通テスト環境ユーティリティ ----------------------------------------


class Env:
    """
    SecretStore を孤立環境で扱うための簡易ラッパ。

    - 一時ディレクトリ配下に users.json / servers.json / master.key 相当を配置
    - SecretStore はコンストラクタ引数でパスを受け取る前提
      (旧環境変数方式ではなく、現行 store.py 実装に合わせる)
    """

    def __init__(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="ss-edge-"))
        self.users = self.tmp / "users.json"
        self.servers = self.tmp / "servers.json"
        self.master = self.tmp / "master.key"

    def new_store(self) -> SecretStore:
        """
        現在のファイル群を前提に SecretStore を生成。
        """
        return SecretStore(
            users_path=self.users,
            servers_path=self.servers,
            masterkey_path=self.master,
        )

    def cleanup(self) -> None:
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


# --- テスト本体 (関数スタイル) --------------------------------------------


def test_01_put_user_empty_provider_raises_value_error() -> None:
    """
    provider="" の put_user は ValueError を送出すること。
    """
    env = Env()
    try:
        ss = env.new_store()
        try:
            ss.put_user(1, "", b"X")
            raise AssertionError("ValueError が送出されていない")
        except ValueError:
            pass
    finally:
        env.cleanup()


def test_02_put_server_empty_provider_raises_value_error() -> None:
    """
    provider="" の put_server は ValueError を送出すること。
    """
    env = Env()
    try:
        ss = env.new_store()
        try:
            ss.put_server(1, "", b"X")
            raise AssertionError("ValueError が送出されていない")
        except ValueError:
            pass
    finally:
        env.cleanup()


def test_03_get_user_empty_provider_returns_none() -> None:
    """
    provider="" の get_user は None を返すこと。
    """
    env = Env()
    try:
        ss = env.new_store()
        out = ss.get_user_key(1, "")
        assert out is None
    finally:
        env.cleanup()


def test_04_get_server_empty_provider_returns_none() -> None:
    """
    provider="" の get_server は None を返すこと。
    """
    env = Env()
    try:
        ss = env.new_store()
        out = ss.get_server_key(1, "")
        assert out is None
    finally:
        env.cleanup()


def test_05_has_server_any_key_false_then_true() -> None:
    """
    has_server_any_key:
    - 何も登録されていない場合 False
    - いずれか provider のキー登録後は True
    """
    env = Env()
    try:
        ss = env.new_store()
        assert ss.has_server_any_key(10) is False

        ss.put_server(10, "openai", b"X")
        assert ss.has_server_any_key(10) is True
    finally:
        env.cleanup()


def test_06_delete_server_keys_safe() -> None:
    """
    delete_server_keys:
    - 未登録でも例外にならず安全に終了すること。
    """
    env = Env()
    try:
        ss = env.new_store()
        # 未登録削除
        ss.delete_server_keys(10)

        # 登録後削除しても例外なし
        ss.put_server(10, "openai", b"X")
        ss.delete_server_keys(10)
    finally:
        env.cleanup()


def test_07_backward_compat_no_prefix() -> None:
    """
    旧フォーマット (provider を key の JSON 直下に持つ想定) があれば読み取れること。
    現行実装に互換コードが残っている前提で検証。
    """
    env = Env()
    try:
        # 旧形式 JSON を直接書き込み
        data = {
            # provider 直下に暗号文を置く旧構造を想定
            "1": {"openai": SecretStore._enc(b"OLD", b"0" * 32).decode("ascii")},
        }
        env.users.write_text(json.dumps(data), encoding="utf-8")

        ss = env.new_store()
        out = ss.get_user_key(1, "openai")
        assert out == b"OLD"
    finally:
        env.cleanup()


def test_08_broken_json_is_recovered_to_empty() -> None:
    """
    users.json が壊れている場合:
    - 読み込みエラーを検出して復旧 (空 dict 保存) されること。
    """
    env = Env()
    try:
        env.users.write_text("{ invalid json", encoding="utf-8")
        ss = env.new_store()
        # 復旧後は get_user_keys が空 dict を返す想定
        assert ss.get_user_keys(1) == {}
    finally:
        env.cleanup()


def test_09_delete_user_keys_clears_providers() -> None:
    """
    delete_user_keys:
    - 指定ユーザー配下の provider キーを全削除すること。
    """
    env = Env()
    try:
        ss = env.new_store()
        ss.put_user(1, "openai", b"A")
        ss.put_user(1, "gemini", b"B")
        ss.put_user(2, "openai", b"C")

        ss.delete_user_keys(1)

        assert ss.get_user_keys(1) == {}
        assert ss.get_user_keys(2) != {}
    finally:
        env.cleanup()


# --- mapping / エントリポイント -------------------------------------------

mapping = {
    "test_01_put_user_empty_provider_raises_value_error":
        ("M01:T01-02-01", "put_user: provider空 -> ValueError"),
    "test_02_put_server_empty_provider_raises_value_error":
        ("M01:T01-02-02", "put_server: provider空 -> ValueError"),
    "test_03_get_user_empty_provider_returns_none":
        ("M01:T01-02-03", "get_user: provider空 -> None"),
    "test_04_get_server_empty_provider_returns_none":
        ("M01:T01-02-04", "get_server: provider空 -> None"),
    "test_05_has_server_any_key_false_then_true":
        ("M01:T01-02-05", "has_server_any_key False/True"),
    "test_06_delete_server_keys_safe":
        ("M01:T01-02-06", "delete_server_keys 安全"),
    "test_07_backward_compat_no_prefix":
        ("M01:T01-02-07", "旧prefixなし互換"),
    "test_08_broken_json_is_recovered_to_empty":
        ("M01:T01-02-08", "壊れJSON復旧"),
    "test_09_delete_user_keys_clears_providers":
        ("M01:T01-02-09", "delete_user_keys 全削除"),
}


if __name__ == "__main__":
    run_unittest_suite("M01:T01-02", mapping, globals())
