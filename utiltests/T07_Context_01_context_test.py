# -*- coding: utf-8 -*-
"""
context_test.py
- message.build_context() 相当のコンテキスト組み立てテストの雛形
- まだDiscordイベント層に依存が残るため、既定では SKIP
- 将来、引数を dict で受けられるよう抽象化してから有効化
"""
import unittest
import os

@unittest.skip("build_context のDiscord依存を剥がしてから有効化する予定")
class ContextBuildTest(unittest.TestCase):
    def test_build_context_skeleton(self):
        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
