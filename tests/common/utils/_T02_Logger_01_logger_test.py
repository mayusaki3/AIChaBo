# -*- coding: utf-8 -*-
"""
COMMON-UTILS:T02 : logger

対象: common.utils.logger

目的:
- logger 初期化分岐（handlers あり/なし）を網羅する
- log_info / log_warn が例外なく出力されること
- log_error が redact を通して出力されること（マスクされること）

注意:
- common.utils.logger は import 時に logging.getLogger("aichabo") の handlers を見て初期化する。
  同一プロセス内で handlers が残るため、テスト内で明示的に退避・復元する。
"""

import io
import importlib
import logging
import unittest
from typing import Dict, Tuple

from tests._report import run_unittest_suite


class LoggerTest(unittest.TestCase):
    def setUp(self):
        # 共有ロガーを退避
        self._logger = logging.getLogger("aichabo")
        self._orig_handlers = list(self._logger.handlers)
        self._orig_level = self._logger.level
        self._orig_propagate = self._logger.propagate

        # テスト用に出力を捕捉
        self._buf = io.StringIO()
        self._capture_handler = logging.StreamHandler(self._buf)
        self._capture_handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))

        # いったん handlers を完全に差し替える（初期化分岐の制御を容易にする）
        self._logger.handlers = []
        self._logger.propagate = False

    def tearDown(self):
        # 復元
        self._logger.handlers = self._orig_handlers
        self._logger.setLevel(self._orig_level)
        self._logger.propagate = self._orig_propagate

    def _reload_logger_module(self):
        import common.utils.logger as L  # type: ignore
        return importlib.reload(L)

    def _read_output(self) -> str:
        return self._buf.getvalue()

    # [COMMON-UTILS:T02-01-01] 初期化分岐：handlers なし → handler 追加 + level=INFO
    def test_01_init_adds_handler_when_no_handlers(self):
        # handlers なしの状態で reload して初期化を踏む
        L = self._reload_logger_module()

        # 追加された handler を capture に置換して出力を検証しやすくする
        self._logger.handlers = [self._capture_handler]

        self.assertGreaterEqual(len(self._logger.handlers), 1)
        self.assertEqual(self._logger.level, logging.INFO)

        L.log_info("hello")
        self.assertIn("[INFO] hello", self._read_output())

    # [COMMON-UTILS:T02-01-02] 初期化分岐：handlers あり → 追加しない（重複防止）
    def test_02_init_does_not_add_handler_when_exists(self):
        # 事前に handler を1つ入れておく → reload しても増えない
        self._logger.handlers = [self._capture_handler]
        before = len(self._logger.handlers)

        _ = self._reload_logger_module()
        after = len(self._logger.handlers)

        self.assertEqual(after, before)

    # [COMMON-UTILS:T02-01-03] log_warn：warning で出力される
    def test_03_log_warn_outputs_warning(self):
        L = self._reload_logger_module()
        self._logger.handlers = [self._capture_handler]

        L.log_warn("careful")
        self.assertIn("[WARNING] careful", self._read_output())

    # [COMMON-UTILS:T02-01-04] log_error：redact を通して出力される（api_key がマスク）
    def test_04_log_error_redacts_message(self):
        L = self._reload_logger_module()
        self._logger.handlers = [self._capture_handler]

        L.log_error("api_key=ABCDEFGH12345678")
        out = self._read_output()
        self.assertIn("[ERROR] api_key=***", out)


if __name__ == "__main__":
    mapping: Dict[str, Tuple[str, str]] = {
        "test_01_init_adds_handler_when_no_handlers": ("COMMON-UTILS:T02-01-01", "初期化：handlers なし → handler追加 + level=INFO"),
        "test_02_init_does_not_add_handler_when_exists": ("COMMON-UTILS:T02-01-02", "初期化：handlers あり → 追加しない（重複防止）"),
        "test_03_log_warn_outputs_warning": ("COMMON-UTILS:T02-01-03", "log_warn：warning 出力"),
        "test_04_log_error_redacts_message": ("COMMON-UTILS:T02-01-04", "log_error：redact を通して出力（api_key マスク）"),
    }
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(LoggerTest)
    run_unittest_suite("COMMON-UTILS:T02 common/utils/logger", suite, mapping)
