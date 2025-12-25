# -*- coding: utf-8 -*-
"""
COMMON-UTILS:T06 : prefetch

対象: common.utils.prefetch

目的:
- prefetch_doc_summaries() のガード / 正常系 / 例外系 / sig 丸め（最大8）を検証する
- read_urls / format_read_results_for_llm を patch して外部依存を排除する

テスト番号:
- COMMON-UTILS:T06-01-01 ...（T06=prefetch, 01=テストコード, 01..=ケース）

実行:
- python -m tests.common.utils.T06_Prefetch_01_prefetch_test
"""

import asyncio
import unittest
from typing import Any, Dict, List, Tuple
from unittest.mock import patch

from tests._report import run_unittest_suite


def _run(coro):
    return asyncio.run(coro)


class PrefetchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from common.utils import prefetch as mod  # type: ignore
        cls.mod = mod

        fn = getattr(mod, "prefetch_doc_summaries", None)
        if not callable(fn):
            raise AttributeError("prefetch_doc_summaries not found in common.utils.prefetch")

        # ★重要: クラス属性にそのまま入れると descriptor により self が注入される
        cls.fn = staticmethod(fn)

    # [COMMON-UTILS:T06-01-01] urls=None -> ("", ())
    def test_01_urls_none_returns_empty_tuple(self):
        out_text, out_sig = _run(self.fn(None))  # type: ignore[arg-type]
        self.assertEqual(out_text, "")
        self.assertEqual(out_sig, tuple())

    # [COMMON-UTILS:T06-01-02] urls=[] -> ("", ())
    def test_02_urls_empty_returns_empty_tuple(self):
        out_text, out_sig = _run(self.fn([]))
        self.assertEqual(out_text, "")
        self.assertEqual(out_sig, tuple())

    # [COMMON-UTILS:T06-01-03] urls に空要素が混じっても除去され、空なら ("", ())
    def test_03_urls_filters_falsy(self):
        out_text, out_sig = _run(self.fn(["", None, ""]))  # type: ignore[list-item]
        self.assertEqual(out_text, "")
        self.assertEqual(out_sig, tuple())

    # [COMMON-UTILS:T06-01-04] 正常: read_urls -> format -> (formatted, sig) / sig は最大8
    def test_04_happy_path_formats_and_sig_is_capped_to_8(self):
        urls = [f"https://e/{i}" for i in range(20)]
        fake_items = [{"url": u, "title": f"t{i}", "text": f"body{i}"} for i, u in enumerate(urls)]

        async def _fake_read_urls(_urls: List[str], **kwargs: Any) -> Any:
            return fake_items

        def _fake_format(items: Any, **kwargs: Any) -> str:
            return "FORMATTED"

        with patch("common.utils.prefetch.read_urls", new=_fake_read_urls), \
             patch("common.utils.prefetch.format_read_results_for_llm", new=_fake_format):
            out_text, out_sig = _run(self.fn(urls))

        self.assertEqual(out_text, "FORMATTED")
        self.assertIsInstance(out_sig, tuple)
        self.assertEqual(out_sig, tuple(urls[:8]))

    # [COMMON-UTILS:T06-01-05] read_urls が例外 -> 例外はそのまま（握り潰さない）
    def test_05_read_urls_raises_propagates(self):
        urls = ["https://e/1"]

        async def _boom(_urls: List[str], **kwargs: Any) -> Any:
            raise RuntimeError("boom")

        with patch("common.utils.prefetch.read_urls", new=_boom):
            with self.assertRaises(RuntimeError):
                _ = _run(self.fn(urls))

    # [COMMON-UTILS:T06-01-06] 呼び出し引数: read_urls へ expected kwargs が渡る
    def test_06_read_urls_called_with_expected_kwargs(self):
        urls = ["https://e/1"]
        calls: List[Dict[str, Any]] = []

        async def _spy_read_urls(_urls: List[str], **kwargs: Any) -> Any:
            calls.append({"urls": list(_urls), "kwargs": dict(kwargs)})
            return []

        def _fake_format(items: Any, **kwargs: Any) -> str:
            return ""

        with patch("common.utils.prefetch.read_urls", new=_spy_read_urls), \
             patch("common.utils.prefetch.format_read_results_for_llm", new=_fake_format):
            out_text, out_sig = _run(self.fn(urls, max_chars=123, max_bytes=456, language_hint="en"))

        self.assertEqual(out_text, "")
        self.assertEqual(out_sig, tuple(urls[:8]))
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["urls"], urls)

        kw = calls[0]["kwargs"]
        self.assertEqual(kw.get("max_bytes"), 456)
        self.assertEqual(kw.get("max_chars"), 123)
        self.assertEqual(kw.get("follow_pdfs"), True)
        self.assertEqual(kw.get("extract_images"), False)
        self.assertEqual(kw.get("analyze_images"), False)
        self.assertEqual(kw.get("language_hint"), "en")
        self.assertEqual(kw.get("require_citations"), False)


if __name__ == "__main__":
    mapping: Dict[str, Tuple[str, str]] = {
        "test_01_urls_none_returns_empty_tuple": ("COMMON-UTILS:T06-01-01", "urls=None -> ('', ())"),
        "test_02_urls_empty_returns_empty_tuple": ("COMMON-UTILS:T06-01-02", "urls=[] -> ('', ())"),
        "test_03_urls_filters_falsy": ("COMMON-UTILS:T06-01-03", "urls の空要素は除去される"),
        "test_04_happy_path_formats_and_sig_is_capped_to_8": ("COMMON-UTILS:T06-01-04", "正常: format + sig最大8"),
        "test_05_read_urls_raises_propagates": ("COMMON-UTILS:T06-01-05", "read_urls例外は伝播"),
        "test_06_read_urls_called_with_expected_kwargs": ("COMMON-UTILS:T06-01-06", "read_urls 呼び出し引数検証"),
    }
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(PrefetchTest)
    run_unittest_suite("COMMON-UTILS:T06 common/utils/prefetch", suite, mapping)
