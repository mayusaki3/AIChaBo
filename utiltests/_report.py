# utiltests/_report.py
# 統一出力: [Txx-yy] タイトル ... OK / NG
from contextlib import contextmanager
import traceback
from typing import Dict, Tuple
import unittest

class _Reporter:
    def __init__(self, suite_id: str):
        self.suite_id = suite_id  # 例: "T05-01"
        self.ok = 0
        self.ng = 0
        self.seq = 0

    def banner(self, title: str):
        print(f"=== {self.suite_id} {title} ===")

    @contextmanager
    def case(self, title: str):
        """スクリプト系テストでの1ケース。例: with rep.case('openai echo'): ..."""
        self.seq += 1
        tid = f"{self.suite_id}-{self.seq:02d}"
        print(f"[{tid}] {title} ... ", end="", flush=True)
        try:
            yield tid
        except Exception as e:
            self.ng += 1
            print("NG")
            print(f"[{tid}] {type(e).__name__}: {e}")
            tb = traceback.format_exc(limit=3)
            print(tb.strip())
        else:
            self.ok += 1
            print("OK")

    def summary(self):
        total = self.ok + self.ng
        print(f"--- SUMMARY {self.suite_id}: OK={self.ok} / NG={self.ng} / TOTAL={total} ---")

def make_reporter(suite_id: str) -> _Reporter:
    return _Reporter(suite_id)

# ==== unittest 連携（各 test_* を「OK/NG」で逐次表示） ====

class VerboseResult(unittest.TextTestResult):
    """unittest の各テストに ID/タイトルを割り当てて OK/NG を標準出力。"""
    def __init__(self, *a, reporter: _Reporter, mapping: Dict[str, Tuple[str, str]], **kw):
        super().__init__(*a, **kw)
        self._rep = reporter
        self._map = mapping  # メソッド名 -> (TID, タイトル)

    def _lookup(self, test) -> Tuple[str, str]:
        key = test.id().split(".")[-1]  # test_xxx
        return self._map.get(key, (f"{self._rep.suite_id}-??", key))

    def addSuccess(self, test):
        super().addSuccess(test)
        tid, title = self._lookup(test)
        self._rep.ok += 1
        print(f"[{tid}] {title} ... OK")

    def addFailure(self, test, err):
        super().addFailure(test, err)
        tid, title = self._lookup(test)
        self._rep.ng += 1
        print(f"[{tid}] {title} ... NG")
        self._rep.stream.writeln(self._exc_info_to_string(err, test))

    def addError(self, test, err):
        super().addError(test, err)
        tid, title = self._lookup(test)
        self._rep.ng += 1
        print(f"[{tid}] {title} ... NG")
        self._rep.stream.writeln(self._exc_info_to_string(err, test))

def run_unittest_suite(suite_id: str, suite: unittest.TestSuite, mapping: Dict[str, Tuple[str, str]]):
    rep = make_reporter(suite_id)
    rep.banner("unittest suite")
    runner = unittest.TextTestRunner(
        verbosity=0,
        resultclass=lambda *a, **kw: VerboseResult(*a, reporter=rep, mapping=mapping, **kw)
    )
    runner.run(suite)
    rep.summary()
