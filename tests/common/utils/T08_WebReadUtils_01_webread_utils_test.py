# -*- coding: utf-8 -*-
"""
COMMON-UTILS:T08 : webread_utils

対象: common.utils.webread_utils

目的:
- 純関数ユーティリティ（clean/guess/title/noise/pick/summarize/header）
- read_urls の主要分岐（exception/status>=400/pdf/text-like/html/parsefail）
- format_read_results_for_llm の主要分岐（error/normal/citations/pdf/images）

実行:
- python -m tests.common.utils.T08_WebReadUtils_01_webread_utils_test
"""

import asyncio
import unittest
from typing import Any, Dict, List, Tuple
from unittest.mock import patch

from tests._report import run_unittest_suite


def _run(coro):
    return asyncio.run(coro)


class WebReadUtilsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from common.utils import webread_utils as mod  # type: ignore
        cls.mod = mod

    # --------
    # 純関数
    # --------

    # [COMMON-UTILS:T08-01-01] redact: 代表的secretのマスク
    def test_01_redact_masks_secret_like(self):
        s = "token=sk-1234567890ABCDEFGHijklmnopQRST"
        out = self.mod.redact(s)
        self.assertIn("sk-", out)
        self.assertIn("…", out)
        self.assertNotEqual(out, s)

    # [COMMON-UTILS:T08-01-02] _clean_whitespace: 空白圧縮
    def test_02_clean_whitespace(self):
        out = self.mod._clean_whitespace(" a \n  b\tc  ")
        self.assertEqual(out, "a b c")

    # [COMMON-UTILS:T08-01-03] _filename_from_url
    def test_03_filename_from_url(self):
        self.assertEqual(self.mod._filename_from_url("https://x/a.txt"), "a.txt")
        self.assertEqual(self.mod._filename_from_url("https://x/"), "")

    # [COMMON-UTILS:T08-01-04] _is_html_ctype / _is_text_like
    def test_04_type_guesses(self):
        self.assertTrue(self.mod._is_html_ctype("text/html; charset=utf-8"))
        self.assertTrue(self.mod._is_text_like("text/plain", "https://x/a.bin"))
        self.assertTrue(self.mod._is_text_like("application/octet-stream", "https://x/a.md"))
        self.assertFalse(self.mod._is_text_like("application/octet-stream", "https://x/a.bin"))

    # [COMMON-UTILS:T08-01-05] _decode_text: utf-8 / cp932 / replace
    def test_05_decode_text_fallbacks(self):
        self.assertEqual(self.mod._decode_text("あ".encode("utf-8")), "あ")
        # cp932でしか読めない想定のバイト列（"表" 等でなく安全な範囲）
        raw = "テスト".encode("cp932")
        self.assertIn("テスト", self.mod._decode_text(raw))
        # どうしても無理なら replace 経由で落ちない
        raw2 = bytes([0xFF, 0xFE, 0xFD])
        out2 = self.mod._decode_text(raw2)
        self.assertIsInstance(out2, str)
        self.assertTrue(len(out2) > 0)

    # [COMMON-UTILS:T08-01-06] _summarize_code: 省略あり/なし
    def test_06_summarize_code(self):
        txt = "\n".join([f"line{i}" for i in range(200)])
        out = self.mod._summarize_code(txt, max_chars=100, max_lines=5)
        self.assertIn("```text", out)
        self.assertIn("（長文のため一部省略）", out)

        short = "a\nb\nc"
        out2 = self.mod._summarize_code(short, max_chars=1000, max_lines=100)
        self.assertIn("```text", out2)
        self.assertNotIn("一部省略", out2)

    # [COMMON-UTILS:T08-01-07] HTML抽出: title/published/noise/main/images
    def test_07_html_extract_helpers(self):
        html_bytes = b"""
        <html>
          <head>
            <meta property="og:title" content="OG TITLE"/>
            <meta property="article:published_time" content="2025-01-02"/>
            <style>.x{}</style>
            <script>1</script>
          </head>
          <body>
            <header>HEAD</header>
            <main>
              <article>
                <div>hello world</div>
                <img src="/a.png"/>
                <img src="//cdn.example.com/b.png"/>
              </article>
            </main>
            <footer>FOOT</footer>
          </body>
        </html>
        """
        doc = self.mod._parse_html(html_bytes)
        self.assertIsNotNone(doc)

        self.mod._drop_noise(doc)
        title = self.mod._extract_title(doc)
        pub = self.mod._guess_published(doc)
        main = self.mod._pick_main_block(doc)
        imgs = self.mod._collect_images(doc, "https://example.com/x", limit=6)

        self.assertEqual(title, "OG TITLE")
        self.assertEqual(pub, "2025-01-02")
        self.assertIn("hello world", main)
        self.assertIn("https://example.com/a.png", imgs)
        self.assertIn("https://cdn.example.com/b.png", imgs)

    # [COMMON-UTILS:T08-01-08] _build_request_headers: Authorization の許可/拒否
    def test_08_build_request_headers_auth_rules(self):
        # GitHub host には Authorization を付けない
        h1 = self.mod._build_request_headers("https://github.com/a", {"Authorization": "Bearer X"})
        self.assertIn("User-Agent", h1)
        self.assertNotIn("Authorization", h1)

        # LLM_AUTH_HOSTS には Authorization を付ける
        h2 = self.mod._build_request_headers("https://api.openai.com/v1", {"Authorization": "Bearer X"})
        self.assertEqual(h2.get("Authorization"), "Bearer X")

        # その他 host には Authorization を付けない（明示ルール外）
        h3 = self.mod._build_request_headers("https://example.com/x", {"Authorization": "Bearer X"})
        self.assertNotIn("Authorization", h3)

        # その他ヘッダは付与
        h4 = self.mod._build_request_headers("https://example.com/x", {"X-Test": "1"})
        self.assertEqual(h4.get("X-Test"), "1")

    # -----------------
    # read_urls 本体分岐
    # -----------------

    # [COMMON-UTILS:T08-01-09] read_urls: _fetch が例外 -> error entry
    def test_09_read_urls_fetch_exception(self):
        async def _fake_fetch(session, url, max_bytes, req_headers=None):
            raise RuntimeError("boom")

        with patch("common.utils.webread_utils._fetch", new=_fake_fetch):
            items = _run(self.mod.read_urls(["https://e/1"], require_citations=False))
        self.assertEqual(len(items), 1)
        self.assertIn("error", items[0])
        self.assertIn("boom", items[0]["error"])

    # [COMMON-UTILS:T08-01-10] read_urls: status>=400 JSON payload message
    def test_10_read_urls_http_error_json_message(self):
        async def _fake_fetch(session, url, max_bytes, req_headers=None):
            raw = b'{"message":"sk-1234567890ABCDEFGHijklmnopQRST"}'
            return raw, "application/json", 401

        with patch("common.utils.webread_utils._fetch", new=_fake_fetch):
            items = _run(self.mod.read_urls(["https://e/1"], require_citations=False))
        self.assertIn("error", items[0])
        self.assertIn("HTTP 401", items[0]["error"])
        # redact で … を含む形になる
        self.assertIn("…", items[0]["error"])

    # [COMMON-UTILS:T08-01-11] read_urls: status>=400 非JSON snippet
    def test_11_read_urls_http_error_non_json_snippet(self):
        async def _fake_fetch(session, url, max_bytes, req_headers=None):
            raw = b"<html>error body</html>"
            return raw, "text/html", 500

        with patch("common.utils.webread_utils._fetch", new=_fake_fetch):
            items = _run(self.mod.read_urls(["https://e/1"], require_citations=False))
        self.assertIn("error", items[0])
        self.assertIn("HTTP 500", items[0]["error"])
        self.assertIn("error body", items[0]["error"])

    # [COMMON-UTILS:T08-01-12] read_urls: PDF 分岐
    def test_12_read_urls_pdf(self):
        async def _fake_fetch(session, url, max_bytes, req_headers=None):
            return b"%PDF-1.7", "application/pdf", 200

        with patch("common.utils.webread_utils._fetch", new=_fake_fetch):
            items = _run(self.mod.read_urls(["https://e/a.pdf"], require_citations=False))
        self.assertTrue(items[0].get("is_pdf"))
        self.assertIn("PDF", items[0].get("note", ""))

    # [COMMON-UTILS:T08-01-13] read_urls: text-like 分岐（非HTML）
    def test_13_read_urls_text_like(self):
        async def _fake_fetch(session, url, max_bytes, req_headers=None):
            return "hello\nworld".encode("utf-8"), "text/plain", 200

        with patch("common.utils.webread_utils._fetch", new=_fake_fetch):
            items = _run(self.mod.read_urls(["https://e/a.txt"], require_citations=False))
        it = items[0]
        self.assertEqual(it.get("title"), "a.txt")
        self.assertIn("```text", it.get("summary", ""))
        self.assertIn("raw", it)

    # [COMMON-UTILS:T08-01-14] read_urls: HTML parse fail -> error
    def test_14_read_urls_html_parse_fail(self):
        async def _fake_fetch(session, url, max_bytes, req_headers=None):
            return b"<html><bad", "text/html", 200

        with patch("common.utils.webread_utils._fetch", new=_fake_fetch), \
             patch("common.utils.webread_utils._parse_html", new=lambda raw: None):
            items = _run(self.mod.read_urls(["https://e/1"], require_citations=False))
        self.assertIn("error", items[0])
        self.assertIn("HTML解析に失敗", items[0]["error"])

    # [COMMON-UTILS:T08-01-15] read_urls: HTML happy path（images/off）
    def test_15_read_urls_html_happy_path(self):
        html_bytes = b"""
        <html><head><title>TT</title></head>
        <body><main><div id="main">Hello <b>World</b></div></main></body></html>
        """

        async def _fake_fetch(session, url, max_bytes, req_headers=None):
            return html_bytes, "text/html; charset=utf-8", 200

        with patch("common.utils.webread_utils._fetch", new=_fake_fetch):
            items = _run(self.mod.read_urls(["https://e/1"], extract_images=False, require_citations=False))
        it = items[0]
        self.assertEqual(it.get("title"), "TT")
        self.assertIn("Hello World", it.get("text", ""))
        self.assertIsInstance(it.get("images"), list)
        self.assertEqual(it.get("images"), [])

    # -------------------------
    # format_read_results_for_llm
    # -------------------------

    # [COMMON-UTILS:T08-01-16] format: error item / normal item / citations
    def test_16_format_read_results_for_llm(self):
        items = [
            {"url": "u1", "error": "oops"},
            {"url": "u2", "title": "T", "published": "2025-01-01", "summary": "S", "images": ["i1", "i2"], "is_pdf": False},
            {"url": "u3", "title": "", "is_pdf": True, "images": []},
        ]
        s = self.mod.format_read_results_for_llm(items, require_citations=True)
        self.assertIn("**(取得失敗)**", s)
        self.assertIn("**T**", s)
        self.assertIn("Published:", s)
        self.assertIn("Summary:", s)
        self.assertIn("Images:", s)
        self.assertIn("PDF detected", s)
        self.assertIn("Sources:", s)
        self.assertIn("[1] u1", s)


if __name__ == "__main__":
    mapping: Dict[str, Tuple[str, str]] = {
        "test_01_redact_masks_secret_like": ("COMMON-UTILS:T08-01-01", "redact: secret マスク"),
        "test_02_clean_whitespace": ("COMMON-UTILS:T08-01-02", "_clean_whitespace: 圧縮"),
        "test_03_filename_from_url": ("COMMON-UTILS:T08-01-03", "_filename_from_url"),
        "test_04_type_guesses": ("COMMON-UTILS:T08-01-04", "_is_html_ctype/_is_text_like"),
        "test_05_decode_text_fallbacks": ("COMMON-UTILS:T08-01-05", "_decode_text: fallback"),
        "test_06_summarize_code": ("COMMON-UTILS:T08-01-06", "_summarize_code: 省略"),
        "test_07_html_extract_helpers": ("COMMON-UTILS:T08-01-07", "HTML helper 群"),
        "test_08_build_request_headers_auth_rules": ("COMMON-UTILS:T08-01-08", "_build_request_headers: auth ルール"),
        "test_09_read_urls_fetch_exception": ("COMMON-UTILS:T08-01-09", "read_urls: fetch例外"),
        "test_10_read_urls_http_error_json_message": ("COMMON-UTILS:T08-01-10", "read_urls: HTTPエラー JSON"),
        "test_11_read_urls_http_error_non_json_snippet": ("COMMON-UTILS:T08-01-11", "read_urls: HTTPエラー 非JSON"),
        "test_12_read_urls_pdf": ("COMMON-UTILS:T08-01-12", "read_urls: PDF"),
        "test_13_read_urls_text_like": ("COMMON-UTILS:T08-01-13", "read_urls: text-like"),
        "test_14_read_urls_html_parse_fail": ("COMMON-UTILS:T08-01-14", "read_urls: HTML parse失敗"),
        "test_15_read_urls_html_happy_path": ("COMMON-UTILS:T08-01-15", "read_urls: HTML 正常"),
        "test_16_format_read_results_for_llm": ("COMMON-UTILS:T08-01-16", "format_read_results_for_llm"),
    }
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(WebReadUtilsTest)
    run_unittest_suite("COMMON-UTILS:T08 common/utils/webread_utils", suite, mapping)
