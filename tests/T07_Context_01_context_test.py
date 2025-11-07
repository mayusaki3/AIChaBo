# -*- coding: utf-8 -*-
"""
T07_Context_01_context_test.py
目的: build_context 相当の検証（Discord依存を剥がすまで SKIP）
実行例: python -m tests.T07_Context_01_context_test
"""
import unittest
from tests._report import run_unittest_suite

@unittest.skip("build_context のDiscord依存を剥がしてから有効化予定")
class ContextBuildTest(unittest.TestCase):
    def test_01_skeleton(self):
        """ひな形（将来差し替え）"""
        self.assertTrue(True)

if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ContextBuildTest)
    mapping = {"test_01_skeleton": ("T07-01-01", "skeleton")}
    run_unittest_suite("T07-01", suite, mapping)
