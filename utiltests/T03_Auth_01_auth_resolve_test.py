# -*- coding: utf-8 -*-
"""
auth_resolve_test.py
- resolve_auth_and_key() の骨組みテスト
- 🔒 実ストアへの書き込みを伴うため、既定では SKIP
- 有効化: 環境変数 AIChaBo_TEST_ENABLE_AUTH_RESOLVE=1 をセット
  実行:  AIChaBo_TEST_ENABLE_AUTH_RESOLVE=1 python -m utiltests.auth_resolve_test
"""
import os
import unittest

from common.chat.auth import resolve_auth_and_key


class AuthResolveTest(unittest.TestCase):
    @unittest.skipUnless(os.environ.get("AIChaBo_TEST_ENABLE_AUTH_RESOLVE") == "1",
                         "set AIChaBo_TEST_ENABLE_AUTH_RESOLVE=1 to run")
    def test_resolve_without_any_auth(self):
        # 最低限: 何も登録していない状態では空dictが返ること
        got = resolve_auth_and_key(user_id=123, guild_id=456)
        self.assertIsInstance(got, dict)
        self.assertEqual(got, {})

    # 以降、USM/SSM/SecretStoreへの投入ユーティリティ（auth_seed.py）で下準備してから
    # - USMのみ登録 → OK
    # - USM未登録+SSM共有あり → OK
    # - どちらも無し → {}
    # などを段階的に追加予定。


if __name__ == "__main__":
    unittest.main()
