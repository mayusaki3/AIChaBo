# -*- coding: utf-8 -*-
"""
T03_Auth_01_auth_resolve_test.py
目的: resolve_auth_and_key() の最低限の骨組検証（既定SKIP）
実行例: AIChaBo_TEST_ENABLE_AUTH_RESOLVE=1 python -m utiltests.T03_Auth_01_auth_resolve_test
"""
import os
import unittest
from common.chat.auth import resolve_auth_and_key
from utiltests._report import run_unittest_suite

class AuthResolveTest(unittest.TestCase):
    @unittest.skipUnless(os.environ.get("AIChaBo_TEST_ENABLE_AUTH_RESOLVE") == "1",
                         "set AIChaBo_TEST_ENABLE_AUTH_RESOLVE=1 to run")
    def test_01_resolve_without_any_auth(self):
        """未登録時は {} を返す"""
        got = resolve_auth_and_key(user_id=123, guild_id=456)
        self.assertIsInstance(got, dict)
        self.assertEqual(got, {})

if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(AuthResolveTest)
    mapping = {"test_01_resolve_without_any_auth": ("T03-01-01", "resolve without any auth")}
    run_unittest_suite("T03-01", suite, mapping)
