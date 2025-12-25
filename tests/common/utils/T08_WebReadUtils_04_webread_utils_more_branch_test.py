# -*- coding: utf-8 -*-
"""
T08-04 : webread_utils more branch tests
対象: common.utils.webread_utils

目的:
- coverage report の未到達行を埋めるための追加分岐テスト
"""

import asyncio
import unittest
from unittest.mock import patch

from tests._report import run_unittest_suite


def _run(coro):
    # py3.12: get_event_loop() の DeprecationWarning を避ける
    return asyncio.run(coro)


class WebReadUtilsMoreBranchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from common.utils import webread_utils as W  # type: ignore
        cls.mod = W

    # [T08-04-01] _decode_text: utf-8失敗→cp932成功
    def test_01_decode_text_cp932_success(self):
        # "あ" の cp932 バイト列: 0x82 0xA0 (utf-8では不正)
        raw = b"\x82\xa0"
        out = self.mod._decode_text(raw)
        self.assertEqual(out, "あ")

    # [T08-04-02] _parse_html: 1回目失敗→decode(ignore)→再パース成功
    def test_02_parse_html_fallback_success(self):
        # lxml_html.fromstring が bytes だと失敗するように偽装し、
        # fallback の「txt.encode('utf-8')」側で成功させる
        html_text = "<html><body><div>OK</div></body></html>"
        raw = html_text.encode("utf-8")

        real_fromstring = self.mod.lxml_html.fromstring

        def _fake_fromstring(arg):
            # 1回目(bytes)だけ落とす。2回目(bytes)は real で通す。
            if isinstance(arg, (bytes, bytearray)) and not getattr(_fake_fromstring, "_second", False):
                _fake_fromstring._second = True  # type: ignore[attr-defined]
                raise ValueError("boom")
            return real_fromstring(arg)

        with patch.object(self.mod.lxml_html, "fromstring", new=_fake_fromstring):
            doc = self.mod._parse_html(raw)
        self.assertIsNotNone(doc)

    # [T08-04-03] read_urls: HTTP error + JSON(dict) で key を拾って note を拡張（redactも通す）
    def test_03_read_urls_http_error_json_dict_key_pick_and_redact(self):
        # payload["message"] を拾う枝を踏む（key loop の break 側）
        # webread_utils.redact() が反応する secret を入れて、加工されることも確認
        raw = b'{"message": "oops sk-12345678901234567890"}'

        async def _fake_fetch(session, url, max_bytes, req_headers=None):
            return raw, "application/json; charset=utf-8", 400

        with patch("common.utils.webread_utils._fetch", new=_fake_fetch):
            items = _run(self.mod.read_urls(["https://example.com/api"], require_citations=False))

        self.assertEqual(len(items), 1)
        err = items[0]["error"]
        self.assertIn("HTTP 400", err)
        # redact: 先頭4文字 + … + 末尾4文字（例: sk-1…7890）
        self.assertIn("sk-1", err)
        self.assertIn("…", err)
        self.assertIn("7890", err)

    # [T08-04-04] read_urls: text-like で filename が取れず "(text)" タイトルになる
    def test_04_read_urls_text_like_title_fallback_text(self):
        # URL末尾が "/" だと _filename_from_url が "" になりやすい
        raw = b"hello\nworld\n"

        async def _fake_fetch(session, url, max_bytes, req_headers=None):
            return raw, "text/plain; charset=utf-8", 200

        with patch("common.utils.webread_utils._fetch", new=_fake_fetch):
            items = _run(self.mod.read_urls(["https://example.com/"], extract_images=False, require_citations=False))

        self.assertEqual(len(items), 1)
        it = items[0]
        self.assertEqual(it.get("title"), "(text)")
        self.assertIn("```text", it.get("summary", ""))
        self.assertIn("hello", it.get("summary", ""))

    # [T08-04-05] format_read_results_for_llm: published / is_pdf / images / citations の枝
    def test_05_format_read_results_for_llm_branches(self):
        items = [
            {
                "url": "https://a.example",
                "title": "A",
                "published": "2025-12-25",
                "summary": "SUM",
                "images": ["https://img/1.png", "https://img/2.png", "https://img/3.png", "https://img/4.png"],
                "is_pdf": False,
            },
            {
                "url": "https://b.example/file.pdf",
                "title": "",
                "published": None,
                "summary": "",
                "images": [],
                "is_pdf": True,
            },
        ]
        out = self.mod.format_read_results_for_llm(items, require_citations=True)
        # published/summary/images
        self.assertIn("Published:", out)
        self.assertIn("Summary:", out)
        self.assertIn("Images:", out)
        # pdf note
        self.assertIn("Note: PDF detected.", out)
        # citations
        self.assertIn("Sources:", out)
        self.assertIn("[1]", out)
        self.assertIn("[2]", out)

    # [T08-04-06] format_read_results_for_llm: items空 かつ citations不要
    def test_06_format_read_results_empty(self):
        out = self.mod.format_read_results_for_llm([], require_citations=False)
        self.assertEqual(out, "")


if __name__ == "__main__":
    mapping = {
        "test_01_decode_text_cp932_success": ("COMMON-UTILS:T08-04-01", "_decode_text: utf-8失敗→cp932成功"),
        "test_02_parse_html_fallback_success": ("COMMON-UTILS:T08-04-02", "_parse_html: 1回目失敗→再パース成功"),
        "test_03_read_urls_http_error_json_dict_key_pick_and_redact": ("COMMON-UTILS:T08-04-03", "read_urls: HTTP error JSON(dict) key拾い + redact"),
        "test_04_read_urls_text_like_title_fallback_text": ("COMMON-UTILS:T08-04-04", "read_urls: text-like title='(text)' フォールバック"),
        "test_05_format_read_results_for_llm_branches": ("COMMON-UTILS:T08-04-05", "format_read_results_for_llm: published/pdf/images/citations"),
        "test_06_format_read_results_empty": ("COMMON-UTILS:T08-04-06", "format_read_results_for_llm: items空"),
    }
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(WebReadUtilsMoreBranchTest)
    run_unittest_suite("COMMON-UTILS:T08-04 common/utils/webread_utils more branch", suite, mapping)
