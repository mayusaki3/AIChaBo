# -*- coding: utf-8 -*-
"""
T02-01 SecretStore 基本動作 & 競合整合性テスト
目的:
  - ユーザ/サーバ鍵の put/get が往復で正しく動作する（永続化OK）
  - 複数スレッドの同時 put が発生しても provider 単位で LWW（Last-Write-Wins）
    となり、部分破損が起きない（混在が残らない）
実行例:
  python -m utiltests.T02_SecretStore_01_store_test
出力:
  ✅/❌ と [T02-01-xx] を先頭に持つ行 + SUMMARY（共通レポータ）
注意:
  - 実ファイルへの影響を避けるため、テスト側で SecretStore の保存先を
    テンポラリに差し替えるスイート（T02-02, T02-03, T02-04）も別途用意している。
  - 本スイートは基本機能と LWW を素直に検証する最小構成。
"""

import os
import json
import tempfile
import shutil
import threading
import unittest
from pathlib import Path
from typing import Dict, Any

from utiltests._report import _Reporter as Reporter  # コンテキスト毎に ✅/❌ を出す軽量レポータ
import common.secret.store as store_mod


# === テスト用に SecretStore の保存先をテンポラリへ差し替えるユーティリティ ===

class _TempStoreEnv:
    """ SecretStore が参照するパス（users.json / servers.json / master.key）を一時的に差し替える """
    def __init__(self):
        self._old_USERS = None
        self._old_SERVERS = None
        self._old_MKEY = None
        self._old_env_key = None
        self.root = None
        self.store_dir = None
        self.users = None
        self.servers = None
        self.mkey = None

    def __enter__(self):
        self.root = Path(tempfile.mkdtemp(prefix="aichabo_ss_T0201_"))
        self.store_dir = self.root / "secretstore"
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self.users = self.store_dir / "users.json"
        self.servers = self.store_dir / "servers.json"
        self.mkey = self.root / "master.key"

        # モジュール定数を退避し差し替え
        self._old_USERS = store_mod.USERS_JSON
        self._old_SERVERS = store_mod.SERVERS_JSON
        self._old_MKEY = store_mod.MASTER_KEY_PATH
        self._old_env_key = os.environ.get("AC_MASTER_KEY")

        store_mod.USERS_JSON = self.users
        store_mod.SERVERS_JSON = self.servers
        store_mod.MASTER_KEY_PATH = self.mkey
        # master.key 自動生成（envキーは未使用）
        os.environ.pop("AC_MASTER_KEY", None)

        # 新しい SecretStore を構築
        self.store = store_mod.SecretStore()
        return self

    def __exit__(self, exc_type, exc, tb):
        # 復元
        store_mod.USERS_JSON = self._old_USERS
        store_mod.SERVERS_JSON = self._old_SERVERS
        store_mod.MASTER_KEY_PATH = self._old_MKEY
        if self._old_env_key is not None:
            os.environ["AC_MASTER_KEY"] = self._old_env_key
        else:
            os.environ.pop("AC_MASTER_KEY", None)
        shutil.rmtree(self.root, ignore_errors=True)


def _writer_thread_user(store, uid: int, prov: str, payload: bytes):
    """ user key 用の書き込みスレッドターゲット """
    store.put_user_key(uid, prov, payload)


def _writer_thread_server(store, gid: int, prov: str, payload: bytes):
    """ server key 用の書き込みスレッドターゲット """
    store.put_server_key(gid, prov, payload)


# === 実テスト ===

if __name__ == "__main__":
    rep = Reporter("T02-01 SecretStore basic & concurrency")

    # [T02-01-01] user鍵: put-get roundtrip（基本往復）
    with _TempStoreEnv() as env, rep.case("user roundtrip"):
        ss = env.store
        uid = 1234
        prov = "openai"
        token = b"TOKEN-USER"
        ss.put_user_key(uid, prov, token)
        got = ss.get_user_key(uid, prov)
        assert got == token, "user roundtrip mismatch"

    # [T02-01-02] server鍵: put-get / has_server_any_key / delete（基本往復＋存在確認＋削除）
    with _TempStoreEnv() as env, rep.case("server roundtrip"):
        ss = env.store
        gid = 5678
        prov = "openai"
        token = b"TOKEN-SERVER"
        ss.put_server_key(gid, prov, token)
        assert ss.has_server_any_key(gid) is True, "server keys must exist"
        got = ss.get_server_key(gid, prov)
        assert got == token, "server roundtrip mismatch"
        # 削除して存在しない状態へ
        ss.delete_server_keys(gid)
        assert ss.has_server_any_key(gid) is False, "server keys must be deleted"

    # [T02-01-03] user鍵: 2並列 put → LWW（最後の書き込みが勝つ）＆部分破損なし
    with _TempStoreEnv() as env, rep.case("user concurrent LWW"):
        ss = env.store
        uid = 999
        prov = "openai"
        # 2つの異なるペイロードを並列に書き込む
        t1 = threading.Thread(target=_writer_thread_user, args=(ss, uid, prov, b"AAA"))
        t2 = threading.Thread(target=_writer_thread_user, args=(ss, uid, prov, b"BBB"))
        t1.start(); t2.start(); t1.join(); t2.join()
        last = ss.get_user_key(uid, prov)
        # LWW なので "AAA" or "BBB" のいずれか。かつ混在（部分破損）は起きない
        assert last in (b"AAA", b"BBB"), "not LWW or corrupted content"

    # [T02-01-04] server鍵: 3並列 put → LWW & 破損なし
    with _TempStoreEnv() as env, rep.case("server concurrent LWW"):
        ss = env.store
        gid = 777
        prov = "openai"
        # 3つの異なるペイロードを並列に書き込む
        threads = [
            threading.Thread(target=_writer_thread_server, args=(ss, gid, prov, b"111")),
            threading.Thread(target=_writer_thread_server, args=(ss, gid, prov, b"222")),
            threading.Thread(target=_writer_thread_server, args=(ss, gid, prov, b"333")),
        ]
        for t in threads: t.start()
        for t in threads: t.join()
        last = ss.get_server_key(gid, prov)
        assert last in (b"111", b"222", b"333"), "not LWW or corrupted content"

    rep.summary()
