# -*- coding: utf-8 -*-
"""
T08-03 : webread_utils remaining branch tests
対象: common.utils.webread_utils

目的:
- 既存(T08-01/T08-02)で踏みにくい残り分岐を追加でカバーする
"""

import asyncio
import unittest
from unittest.mock import patch

from tests._report import run_unittest_suite


def _run(coro):
    """async を unittest から呼ぶ補助（py3.12の DeprecationWarning 回避）"""
    return asyncio.run(coro)


class WebReadUtilsRemainingBranchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from common.utils import webread_utils as W  # type: ignore
        cls.mod = W

    # [T08-03-01] _is_text_like: json系ctype True
    def test_01_is_text_like_json_ctype_true(self):
        self.assertTrue(self.mod._is_text_like("application/json; charset=utf-8", "https://x/y"))
        self.assertTrue(self.mod._is_text_like("application/javascript", "https://x/y"))

    # [T08-03-02] _is_text_like: 拡張子推定 True
    def test_02_is_text_like_extension_true(self):
        self.assertTrue(self.mod._is_text_like("application/octet-stream", "https://x/y/test.py"))
        self.assertTrue(self.mod._is_text_like("", "https://x/y/test.md?x=1"))

    # [T08-03-03] _is_text_like: False 側
    def test_03_is_text_like_false(self):
        self.assertFalse(self.mod._is_text_like("application/octet-stream", "https://x/y/bin.dat"))

    # [T08-03-04] _guess_published: 一致で return
    def test_04_guess_published_matches(self):
        raw = b"""
        <html><head>
          <meta property="article:published_time" content="2025-12-25"/>
        </head><body><div>ok</div></body></html>
        """
        doc = self.mod._parse_html(raw)
        self.assertIsNotNone(doc)
        got = self.mod._guess_published(doc)  # type: ignore[arg-type]
        self.assertEqual(got, "2025-12-25")

    # [T08-03-05] _build_request_headers: GitHubはAuthorization破棄
    def test_05_build_request_headers_github_drops_auth(self):
        hdrs = self.mod._build_request_headers(
            "https://github.com/mayusaki3/AIChaBo",
            {"Authorization": "token XXX", "X-Test": "1"},
        )
        self.assertNotIn("Authorization", hdrs)
        self.assertEqual(hdrs.get("X-Test"), "1")
        self.assertIn("User-Agent", hdrs)

    # [T08-03-06] _build_request_headers: LLM hostはAuthorization許可
    def test_06_build_request_headers_llm_allows_auth(self):
        hdrs = self.mod._build_request_headers(
            "https://api.openai.com/v1/models",
            {"Authorization": "Bearer XXX"},
        )
        self.assertEqual(hdrs.get("Authorization"), "Bearer XXX")

    # [T08-03-07] read_urls: snippet空→HTTPのみ
    def test_07_read_urls_http_error_snippet_empty(self):
        async def _fake_fetch(session, url, max_bytes, req_headers=None):
            return b"", "text/plain", 404

        with patch("common.utils.webread_utils._fetch", new=_fake_fetch):
            items = _run(self.mod.read_urls(["https://example.com/x"], require_citations=False))

        self.assertEqual(len(items), 1)
        self.assertIn("error", items[0])
        self.assertEqual(items[0]["error"], "HTTP 404")

    # [T08-03-08] read_urls: json失敗→snippet+redact
    def test_08_read_urls_http_error_json_decode_fails_uses_snippet_and_redact(self):
        # JSON decode を失敗させて except 側(snippet)に落とす
        # snippet には webread_utils.redact が反応する secret パターン(sk-)を入れる
        raw = b"oops sk-12345678901234567890"

        async def _fake_fetch(session, url, max_bytes, req_headers=None):
            return raw, "application/json; charset=utf-8", 400

        def _bad_json_loads(_s: str):
            raise ValueError("boom")

        with patch("common.utils.webread_utils._fetch", new=_fake_fetch), \
             patch("json.loads", new=_bad_json_loads):
            items = _run(self.mod.read_urls(["https://example.com/api"], require_citations=False))

        self.assertEqual(len(items), 1)
        err = items[0]["error"]
        self.assertIn("HTTP 400", err)

        # webread_utils.redact(): 先頭4文字 + "…" + 末尾4文字（例: "sk-1…7890"）
        self.assertIn("sk-1", err)
        self.assertIn("…", err)
        self.assertIn("7890", err)


if __name__ == "__main__":
    mapping = {
        "test_01_is_text_like_json_ctype_true": ("COMMON-UTILS:T08-03-01", "_is_text_like: json系ctype True"),
        "test_02_is_text_like_extension_true": ("COMMON-UTILS:T08-03-02", "_is_text_like: 拡張子推定 True"),
        "test_03_is_text_like_false": ("COMMON-UTILS:T08-03-03", "_is_text_like: False 側"),
        "test_04_guess_published_matches": ("COMMON-UTILS:T08-03-04", "_guess_published: 一致で return"),
        "test_05_build_request_headers_github_drops_auth": ("COMMON-UTILS:T08-03-05", "_build_request_headers: GitHubはAuthorization破棄"),
        "test_06_build_request_headers_llm_allows_auth": ("COMMON-UTILS:T08-03-06", "_build_request_headers: LLM hostはAuthorization許可"),
        "test_07_read_urls_http_error_snippet_empty": ("COMMON-UTILS:T08-03-07", "read_urls: snippet空→HTTPのみ"),
        "test_08_read_urls_http_error_json_decode_fails_uses_snippet_and_redact": ("COMMON-UTILS:T08-03-08", "read_urls: json失敗→snippet+redact"),
    }
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(WebReadUtilsRemainingBranchTest)
    run_unittest_suite("COMMON-UTILS:T08-03 common/utils/webread_utils remaining", suite, mapping)
