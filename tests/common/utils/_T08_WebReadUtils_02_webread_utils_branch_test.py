# -*- coding: utf-8 -*-
"""
COMMON-UTILS:T08-02 : webread_utils (branch)

目的:
- webread_utils.py の残 Miss / BrPart を埋めるための分岐テスト
- 仕様テスト(T08-01)で踏みにくい枝を安全に通す

実行:
- python -m tests.common.utils.T08_WebReadUtils_02_webread_utils_branch_test
"""

import asyncio
import unittest
from typing import Any, Dict, List, Tuple
from unittest.mock import patch

from tests._report import run_unittest_suite


def _run(coro):
    return asyncio.run(coro)


class WebReadUtilsBranchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from common.utils import webread_utils as mod  # type: ignore
        cls.mod = mod

    # [COMMON-UTILS:T08-02-01] redact: 非str/空はそのまま返す（20->exit）
    def test_01_redact_non_str_or_empty(self):
        self.assertEqual(self.mod.redact(None), None)  # type: ignore[arg-type]
        self.assertEqual(self.mod.redact(""), "")

    # [COMMON-UTILS:T08-02-02] _decode_text: utf-8/cp932 も失敗→replace 経路（57-58）
    def test_02_decode_text_replace_fallback(self):
        class _BadBytes:
            """
            bytes.decode を patch できないため、
            decode() が strict のとき常に UnicodeDecodeError を投げる擬似オブジェクトを使う。
            errors='replace' のときだけ成功させることで最終fallback経路を踏む。
            """
            def __init__(self, payload: bytes):
                self._payload = payload

            def decode(self, encoding: str = "utf-8", errors: str = "strict") -> str:
                if errors == "replace":
                    # 最終fallbackは replace で呼ばれる想定
                    return self._payload.decode("utf-8", errors="replace")
                # utf-8/cp932 strict は確実に失敗させる
                raise UnicodeDecodeError(encoding, self._payload, 0, 1, "boom")

        raw = _BadBytes(b"\xff\xfe\xfd")  # type: ignore[var-annotated]
        out = self.mod._decode_text(raw)  # type: ignore[arg-type]
        self.assertIsInstance(out, str)
        self.assertTrue(len(out) > 0)

    # [COMMON-UTILS:T08-02-03] _summarize_code: 省略なし経路（全文返す側）
    def test_03_summarize_code_no_omit(self):
        txt = "a\nb\nc"
        out = self.mod._summarize_code(txt, max_chars=1000, max_lines=100)
        self.assertIn("```text", out)
        self.assertNotIn("一部省略", out)

    # [COMMON-UTILS:T08-02-04] _extract_title: og/twitter/title 全部空 -> ""（101）
    def test_04_extract_title_all_empty(self):
        doc = self.mod._parse_html(b"<html><head></head><body></body></html>")
        self.assertIsNotNone(doc)
        self.assertEqual(self.mod._extract_title(doc), "")

    # [COMMON-UTILS:T08-02-05] _guess_published: 候補があるが日付パターン不一致 -> None（115/121->118）
    def test_05_guess_published_no_match(self):
        raw = b"""
        <html><head>
          <meta name="date" content="yesterday"/>
        </head><body>
          <time>no-date</time>
        </body></html>
        """
        doc = self.mod._parse_html(raw)
        self.assertIsNotNone(doc)
        self.assertIsNone(self.mod._guess_published(doc))

    # [COMMON-UTILS:T08-02-06] _drop_noise: 該当要素が無い場合でも例外なし（129）
    def test_06_drop_noise_no_targets(self):
        doc = self.mod._parse_html(b"<html><body><div>ok</div></body></html>")
        self.assertIsNotNone(doc)
        self.mod._drop_noise(doc)  # 例外なし

    # [COMMON-UTILS:T08-02-07] _pick_main_block: article/main が無い→最大div選択（138->149, 140->139）
    def test_07_pick_main_block_fallback_to_largest_div(self):
        raw = b"""
        <html><body>
          <div>small</div>
          <div>this is a much larger div content with many many words to win</div>
        </body></html>
        """
        doc = self.mod._parse_html(raw)
        self.assertIsNotNone(doc)
        text = self.mod._pick_main_block(doc)
        self.assertIn("much larger", text)

    # [COMMON-UTILS:T08-02-08] _collect_images: 絶対URL/相対/プロトコル相対の混在（152-157, 162-167）
    def test_08_collect_images_url_variants(self):
        raw = b"""
        <html><body>
          <img src="https://abs.example.com/a.png"/>
          <img src="/rel.png"/>
          <img src="//proto.example.com/p.png"/>
        </body></html>
        """
        doc = self.mod._parse_html(raw)
        self.assertIsNotNone(doc)
        imgs = self.mod._collect_images(doc, "https://base.example.com/x", limit=6)
        self.assertIn("https://abs.example.com/a.png", imgs)
        self.assertIn("https://base.example.com/rel.png", imgs)
        self.assertIn("https://proto.example.com/p.png", imgs)

    # [COMMON-UTILS:T08-02-09] _summarize: しきい値以内→そのまま / 超過→末尾…（174）
    def test_09_summarize_threshold(self):
        self.assertEqual(self.mod._summarize("abc", max_chars=10), "abc")
        out = self.mod._summarize("a" * 100, max_chars=10)
        self.assertTrue(out.endswith("…"))
        self.assertEqual(len(out), 10)

    # [COMMON-UTILS:T08-02-10] _build_request_headers: extra が None / 空値は無視（177->182, 180->182, 184）
    def test_10_build_request_headers_extra_none_and_empty_values(self):
        h1 = self.mod._build_request_headers("https://example.com", None)
        self.assertIn("User-Agent", h1)

        h2 = self.mod._build_request_headers("https://example.com", {"X": ""})
        self.assertNotIn("X", h2)

        h3 = self.mod._build_request_headers("https://example.com", {"Authorization": ""})
        self.assertNotIn("Authorization", h3)

    # [COMMON-UTILS:T08-02-11] read_urls: status>=400 JSONだがdictでない→snippet側へ（222->235, 223->222）
    def test_11_read_urls_http_error_json_non_dict_fallback(self):
        async def _fake_fetch(session, url, max_bytes, req_headers=None):
            return b'["not a dict"]', "application/json", 400

        with patch("common.utils.webread_utils._fetch", new=_fake_fetch):
            items = _run(self.mod.read_urls(["https://e/1"], require_citations=False))
        self.assertIn("error", items[0])
        self.assertIn("HTTP 400", items[0]["error"])

    # [COMMON-UTILS:T08-02-12] read_urls: HTML扱いだが _is_text_like False → parse_html へ（233-234 等）
    def test_12_read_urls_non_html_non_text_like_parse_fail(self):
        async def _fake_fetch(session, url, max_bytes, req_headers=None):
            return b"\x00\x01\x02", "application/octet-stream", 200

        with patch("common.utils.webread_utils._fetch", new=_fake_fetch), \
             patch("common.utils.webread_utils._parse_html", new=lambda raw: None):
            items = _run(self.mod.read_urls(["https://e/1"], require_citations=False))
        self.assertIn("error", items[0])
        self.assertIn("HTML解析に失敗", items[0]["error"])

    # [COMMON-UTILS:T08-02-13] read_urls: main 空→doc全文へフォールバック（274）
    def test_13_read_urls_main_empty_fallback_to_doc_text(self):
        html_bytes = b"<html><head><title>T</title></head><body><div>ALLTEXT</div></body></html>"

        async def _fake_fetch(session, url, max_bytes, req_headers=None):
            return html_bytes, "text/html", 200

        with patch("common.utils.webread_utils._fetch", new=_fake_fetch), \
             patch("common.utils.webread_utils._pick_main_block", return_value=""):
            items = _run(self.mod.read_urls(["https://e/1"], extract_images=False, require_citations=False))
        self.assertIn("ALLTEXT", items[0].get("text", ""))

    # [COMMON-UTILS:T08-02-14] read_urls: max_chars トリム分岐（276）
    def test_14_read_urls_trims_to_max_chars(self):
        html_bytes = b"<html><head><title>T</title></head><body><div>" + (b"A" * 200) + b"</div></body></html>"

        async def _fake_fetch(session, url, max_bytes, req_headers=None):
            return html_bytes, "text/html", 200

        with patch("common.utils.webread_utils._fetch", new=_fake_fetch):
            items = _run(self.mod.read_urls(["https://e/1"], max_chars=50, extract_images=False, require_citations=False))
        text = items[0].get("text", "")
        self.assertTrue(len(text) <= 51)

    # [COMMON-UTILS:T08-02-15] format_read_results_for_llm: require_citations False で末尾Sources無し（312->315）
    def test_15_format_no_citations_footer(self):
        items = [{"url": "u", "title": "t", "summary": "s", "images": [], "is_pdf": False}]
        s = self.mod.format_read_results_for_llm(items, require_citations=False)
        self.assertNotIn("Sources:", s)


if __name__ == "__main__":
    mapping: Dict[str, Tuple[str, str]] = {
        "test_01_redact_non_str_or_empty": ("COMMON-UTILS:T08-02-01", "redact: 非str/空はそのまま"),
        "test_02_decode_text_replace_fallback": ("COMMON-UTILS:T08-02-02", "_decode_text: replace fallback"),
        "test_03_summarize_code_no_omit": ("COMMON-UTILS:T08-02-03", "_summarize_code: 省略なし"),
        "test_04_extract_title_all_empty": ("COMMON-UTILS:T08-02-04", "_extract_title: 全部空 -> ''"),
        "test_05_guess_published_no_match": ("COMMON-UTILS:T08-02-05", "_guess_published: 不一致 -> None"),
        "test_06_drop_noise_no_targets": ("COMMON-UTILS:T08-02-06", "_drop_noise: 対象無し"),
        "test_07_pick_main_block_fallback_to_largest_div": ("COMMON-UTILS:T08-02-07", "_pick_main_block: 最大div"),
        "test_08_collect_images_url_variants": ("COMMON-UTILS:T08-02-08", "_collect_images: URL補正"),
        "test_09_summarize_threshold": ("COMMON-UTILS:T08-02-09", "_summarize: 閾値/省略"),
        "test_10_build_request_headers_extra_none_and_empty_values": ("COMMON-UTILS:T08-02-10", "_build_request_headers: extra枝"),
        "test_11_read_urls_http_error_json_non_dict_fallback": ("COMMON-UTILS:T08-02-11", "read_urls: HTTP error JSON非dict"),
        "test_12_read_urls_non_html_non_text_like_parse_fail": ("COMMON-UTILS:T08-02-12", "read_urls: 非text-like parse fail"),
        "test_13_read_urls_main_empty_fallback_to_doc_text": ("COMMON-UTILS:T08-02-13", "read_urls: main空 -> itertext"),
        "test_14_read_urls_trims_to_max_chars": ("COMMON-UTILS:T08-02-14", "read_urls: max_chars trim"),
        "test_15_format_no_citations_footer": ("COMMON-UTILS:T08-02-15", "format: citationsなし"),
    }
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(WebReadUtilsBranchTest)
    run_unittest_suite("COMMON-UTILS:T08-02 common/utils/webread_utils branch", suite, mapping)
