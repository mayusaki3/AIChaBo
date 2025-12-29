# -*- coding: utf-8 -*-
"""
T08-05 : webread_utils last branch tests
対象: common.utils.webread_utils

目的:
- coverage report で残っている未到達行を埋めるための「最後の枝」狙い撃ち
"""

import asyncio
import unittest
from unittest.mock import patch

from tests._report import run_unittest_suite


def _run(coro):
    # py3.12 対応: get_event_loop() DeprecationWarning 回避
    return asyncio.run(coro)


class WebReadUtilsLastBranchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from common.utils import webread_utils as W  # type: ignore
        cls.mod = W

    # [T08-05-01] _parse_html: 通常成功パス（例外なし）
    def test_01_parse_html_success_path(self):
        raw = b"<html><head><title>T</title></head><body><div>OK</div></body></html>"
        doc = self.mod._parse_html(raw)
        self.assertIsNotNone(doc)

    # [T08-05-02] _build_request_headers: Authorization を非許可hostで破棄（GitHubでもLLMでもない）
    def test_02_build_request_headers_drops_authorization_for_other_hosts(self):
        url = "https://example.com/x"
        extra = {
            "Authorization": "Bearer SECRET",
            "X-Test": "1",
            "X-Empty": "",  # 空は skip
        }
        headers = self.mod._build_request_headers(url, extra)
        self.assertIn("User-Agent", headers)
        self.assertIn("X-Test", headers)
        self.assertEqual(headers.get("X-Test"), "1")
        # 非許可hostなので Authorization は入らない
        self.assertNotIn("Authorization", headers)
        # 空値は入らない
        self.assertNotIn("X-Empty", headers)

    # [T08-05-03] read_urls: HTTP error + JSON(dict) だが既知key無し → "HTTP xxx" のみ
    def test_03_read_urls_http_error_json_dict_no_known_keys_keeps_http_only(self):
        raw = b'{"foo": "bar", "baz": 1}'  # key loop で当たらない想定

        async def _fake_fetch(session, url, max_bytes, req_headers=None):
            return raw, "application/json; charset=utf-8", 403

        with patch("common.utils.webread_utils._fetch", new=_fake_fetch):
            items = _run(self.mod.read_urls(["https://example.com/api"], require_citations=False))

        self.assertEqual(len(items), 1)
        err = items[0]["error"]
        self.assertIn("HTTP 403", err)
        # key が拾えないので " — " が付かない（note が伸びない枝）
        self.assertNotIn("—", err)

    # [T08-05-04] read_urls: HTTP error + JSON(dict) で既知keyはあるが値が空 → note は伸びない
    def test_04_read_urls_http_error_json_dict_empty_value_keeps_http_only(self):
        raw = b'{"message": ""}'  # payload.get(key) が falsy

        async def _fake_fetch(session, url, max_bytes, req_headers=None):
            return raw, "application/json; charset=utf-8", 400

        with patch("common.utils.webread_utils._fetch", new=_fake_fetch):
            items = _run(self.mod.read_urls(["https://example.com/api"], require_citations=False))

        self.assertEqual(len(items), 1)
        err = items[0]["error"]
        self.assertIn("HTTP 400", err)
        self.assertNotIn("—", err)

    # [T08-05-05] format_read_results_for_llm: require_citations=True でも items 空なら Sources 行を出さない
    def test_05_format_requires_citations_but_empty_items(self):
        out = self.mod.format_read_results_for_llm([], require_citations=True)
        self.assertEqual(out, "")

    # [T08-05-06] format_read_results_for_llm: title空→(無題) / images無し / pdf無し の枝
    def test_06_format_title_fallback_and_no_images_no_pdf(self):
        items = [
            {
                "url": " https://example.com/x  ",
                "title": "",         # "(無題)" になる
                "published": None,   # Published 行なし
                "summary": "",       # Summary 行なし
                "images": [],        # Images 行なし
                "is_pdf": False,     # Note: PDF detected. なし
            }
        ]
        out = self.mod.format_read_results_for_llm(items, require_citations=False)
        self.assertIn("**(無題)**", out)
        # url の whitespace 圧縮・trim が効く
        self.assertIn("https://example.com/x", out)
        self.assertNotIn("Images:", out)
        self.assertNotIn("Note: PDF detected.", out)


if __name__ == "__main__":
    mapping = {
        "test_01_parse_html_success_path": ("COMMON-UTILS:T08-05-01", "_parse_html: 通常成功パス"),
        "test_02_build_request_headers_drops_authorization_for_other_hosts": ("COMMON-UTILS:T08-05-02", "_build_request_headers: 非許可hostはAuthorization破棄"),
        "test_03_read_urls_http_error_json_dict_no_known_keys_keeps_http_only": ("COMMON-UTILS:T08-05-03", "read_urls: HTTP error + JSON(dict) 既知key無し→HTTPのみ"),
        "test_04_read_urls_http_error_json_dict_empty_value_keeps_http_only": ("COMMON-UTILS:T08-05-04", "read_urls: HTTP error + JSON(dict) 空値→HTTPのみ"),
        "test_05_format_requires_citations_but_empty_items": ("COMMON-UTILS:T08-05-05", "format: citations要求でもitems空→空文字"),
        "test_06_format_title_fallback_and_no_images_no_pdf": ("COMMON-UTILS:T08-05-06", "format: title空→(無題) & images/pdf無し枝"),
    }
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(WebReadUtilsLastBranchTest)
    run_unittest_suite("COMMON-UTILS:T08-05 common/utils/webread_utils last branch", suite, mapping)
