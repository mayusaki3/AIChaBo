# tests/common/utils/T08_WebReadUtils_03_webread_utils_remaining_branch_test.py
# -*- coding: utf-8 -*-
"""
T08-03 : webread_utils 残りの分岐カバー
対象: common.utils.webread_utils

目的:
- read_urls の HTTPエラー時スニペット経路（snippet空/あり）をカバー
- _is_text_like の追加分岐（ctype/拡張子/False）をカバー
- _guess_published の一致return をカバー
- _build_request_headers の GitHub/LLM 認可分岐をカバー

注意:
- webread_utils.redact は "***" ではなく "sk-1…7890" のように省略マスク。
"""

import asyncio
import unittest
from typing import Any, Dict, List, Tuple
from unittest.mock import patch

from tests._report import run_unittest_suite


def _run(coro):
    # Python 3.12: get_event_loop() は非推奨警告になりやすいので asyncio.run を使う
    return asyncio.run(coro)


class WebReadUtilsRemainingBranchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from common.utils import webread_utils as W  # type: ignore
        cls.mod = W

    # [T08-03-01] _is_text_like: json系ctype True
    def test_01_is_text_like_json_ctype_true(self):
        self.assertTrue(self.mod._is_text_like("application/json", "https://example.com/x"))

    # [T08-03-02] _is_text_like: 拡張子推定 True
    def test_02_is_text_like_extension_true(self):
        self.assertTrue(self.mod._is_text_like("application/octet-stream", "https://cdn.example.com/a.py"))

    # [T08-03-03] _is_text_like: False 側
    def test_03_is_text_like_false(self):
        self.assertFalse(self.mod._is_text_like("application/octet-stream", "https://example.com/a.bin"))

    # [T08-03-04] _guess_published: 一致で return
    def test_04_guess_published_match_returns(self):
        raw = b"<html><head><meta name='date' content='2025-01-02'></head><body></body></html>"
        doc = self.mod._parse_html(raw)
        self.assertIsNotNone(doc)
        self.assertEqual(self.mod._guess_published(doc), "2025-01-02")

    # [T08-03-05] _build_request_headers: GitHubはAuthorization破棄
    def test_05_build_request_headers_github_drops_auth(self):
        h = self.mod._build_request_headers(
            "https://github.com/user/repo",
            {"Authorization": "Bearer X", "X-Test": "1"},
        )
        self.assertIn("User-Agent", h)
        self.assertNotIn("Authorization", h)
        self.assertEqual(h.get("X-Test"), "1")

    # [T08-03-06] _build_request_headers: LLM hostはAuthorization許可
    def test_06_build_request_headers_llm_allows_auth(self):
        h = self.mod._build_request_headers(
            "https://api.openai.com/v1/models",
            {"Authorization": "Bearer X"},
        )
        self.assertEqual(h.get("Authorization"), "Bearer X")

    # [T08-03-07] read_urls: snippet空→HTTPのみ
    def test_07_read_urls_http_error_snippet_empty_uses_http_only(self):
        async def _fake_fetch(session, url, max_bytes, req_headers=None):
            # raw が空 → snippet も空 → note は "HTTP xxx" のまま
            return b"", "text/plain", 500

        async def _fake_gather(*tasks, **kwargs):
            # tasks は捨てて、_fake_fetch 相当を返す
            return [(b"", "text/plain", 500)]

        with patch("common.utils.webread_utils._fetch", new=_fake_fetch), \
             patch("common.utils.webread_utils.asyncio.gather", new=_fake_gather):
            items = _run(self.mod.read_urls(["https://example.com/a"]))
        self.assertEqual(len(items), 1)
        self.assertIn("error", items[0])
        self.assertEqual(items[0]["error"], "HTTP 500")

    # [T08-03-08] read_urls: json失敗→snippet+redact（省略マスク）
    def test_08_read_urls_http_error_json_decode_fails_uses_snippet_and_redact(self):
        # JSON decode を必ず失敗させて except 側（snippet取り出し）へ誘導するため、
        # raw は JSONではない文字列にする。
        raw = b"oops sk-1234567890 api_key=ABCDEFGH"

        async def _fake_fetch(session, url, max_bytes, req_headers=None):
            return raw, "text/plain", 400

        async def _fake_gather(*tasks, **kwargs):
            return [(raw, "text/plain", 400)]

        with patch("common.utils.webread_utils._fetch", new=_fake_fetch), \
             patch("common.utils.webread_utils.asyncio.gather", new=_fake_gather):
            items = _run(self.mod.read_urls(["https://example.com/a"]))
        err = items[0]["error"]
        # 期待値は "***" ではなく "sk-1…7890" 形式（先頭4 + … + 末尾4）
        self.assertIn("HTTP 400", err)
        self.assertIn("oops", err)
        self.assertIn("sk-1…7890", err)


if __name__ == "__main__":
    mapping = {
        "test_01_is_text_like_json_ctype_true": ("COMMON-UTILS:T08-03-01", "_is_text_like: json系ctype True"),
        "test_02_is_text_like_extension_true": ("COMMON-UTILS:T08-03-02", "_is_text_like: 拡張子推定 True"),
        "test_03_is_text_like_false": ("COMMON-UTILS:T08-03-03", "_is_text_like: False 側"),
        "test_04_guess_published_match_returns": ("COMMON-UTILS:T08-03-04", "_guess_published: 一致で return"),
        "test_05_build_request_headers_github_drops_auth": ("COMMON-UTILS:T08-03-05", "_build_request_headers: GitHubはAuthorization破棄"),
        "test_06_build_request_headers_llm_allows_auth": ("COMMON-UTILS:T08-03-06", "_build_request_headers: LLM hostはAuthorization許可"),
        "test_07_read_urls_http_error_snippet_empty_uses_http_only": ("COMMON-UTILS:T08-03-07", "read_urls: snippet空→HTTPのみ"),
        "test_08_read_urls_http_error_json_decode_fails_uses_snippet_and_redact": ("COMMON-UTILS:T08-03-08", "read_urls: json失敗→snippet+redact"),
    }
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(WebReadUtilsRemainingBranchTest)
    run_unittest_suite("COMMON-UTILS:T08-03 common/utils/webread_utils remaining", suite, mapping)
