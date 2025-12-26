# tests/common/utils/T08_WebReadUtils_04_webread_utils_uncovered_branch_test.py
# -*- coding: utf-8 -*-
"""
T08-04 : webread_utils 未到達行の追加カバー
対象: common.utils.webread_utils

狙い（coverage report の未到達行を潰す）:
- _pick_main_block: article/main 経路で len(text)>200 の return（line 115）
- _fetch: session.get の正常経路 + max_bytes トリム（line 152-157）
- _parse_html: 2段階失敗で None（line 166-167）
- _collect_images: src=="" continue（line 174）
- _collect_images: base_url 正規表現不一致（180->182） + limit break（184）
- read_urls: HTTPエラー時 snippet decode 例外で内側 except（233-234）
"""

import asyncio
import unittest
from typing import Dict, Optional, Tuple
from unittest.mock import patch

from tests._report import run_unittest_suite


def _run(coro):
    return asyncio.run(coro)


class WebReadUtilsUncoveredBranchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from common.utils import webread_utils as W  # type: ignore
        cls.mod = W

    # [T08-04-01] _pick_main_block: article/main 経路で return (len>200)
    def test_01_pick_main_block_article_return(self):
        body = "a" * 250
        raw = f"<html><body><article>{body}</article></body></html>".encode("utf-8")
        doc = self.mod._parse_html(raw)
        self.assertIsNotNone(doc)
        out = self.mod._pick_main_block(doc)
        self.assertEqual(out, body)

    # [T08-04-02] _fetch: max_bytes トリム + 戻り値形式
    def test_02_fetch_trims_max_bytes(self):
        class _Resp:
            def __init__(self):
                self.headers = {"Content-Type": "text/plain"}
                self.status = 200

            async def read(self):
                return b"X" * 10

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

        class _Session:
            def get(self, url, headers=None, timeout=None, allow_redirects=True):
                return _Resp()

        async def _call():
            raw, ctype, status = await self.mod._fetch(_Session(), "https://example.com", 5, None)
            return raw, ctype, status

        raw, ctype, status = _run(_call())
        self.assertEqual(len(raw), 5)  # トリムが走る
        self.assertEqual(ctype, "text/plain")
        self.assertEqual(status, 200)

    # [T08-04-03] _parse_html: 2段階失敗で None
    def test_03_parse_html_double_fail_returns_none(self):
        with patch("common.utils.webread_utils.lxml_html.fromstring", side_effect=Exception("boom")):
            out = self.mod._parse_html(b"<html></html>")
        self.assertIsNone(out)

    # [T08-04-04] _collect_images: src=="" continue（xpath条件は @src なので空文字で作る）
    def test_04_collect_images_src_empty_is_skipped(self):
        raw = b"<html><body><img src=''><img src='https://a/b.png'></body></html>"
        doc = self.mod._parse_html(raw)
        self.assertIsNotNone(doc)
        imgs = self.mod._collect_images(doc, "https://example.com", limit=6)
        self.assertEqual(imgs, ["https://a/b.png"])

    # [T08-04-05] _collect_images: base_url 正規表現不一致 + limit break
    def test_05_collect_images_base_url_no_match_and_limit_break(self):
        raw = b"<html><body><img src='/x.png'><img src='/y.png'></body></html>"
        doc = self.mod._parse_html(raw)
        self.assertIsNotNone(doc)
        # base_url が "https?://..." 形式でないので m が None になり、"/" 始まりは補正されない
        imgs = self.mod._collect_images(doc, "not-a-url", limit=1)
        self.assertEqual(imgs, ["/x.png"])  # limit=1 で break される

    # [T08-04-06] read_urls: snippet decode 例外で内側 except（233-234）到達
    def test_06_read_urls_snippet_decode_raises_inner_except(self):
        class BadRaw:
            def decode(self, *args, **kwargs):
                raise Exception("decode boom")

            def __len__(self):
                return 10

        bad = BadRaw()

        async def _fake_fetch(session, url, max_bytes, req_headers=None):
            # status>=400 で error 経路へ。json.loads で raw.decode が走って例外→exceptへ。
            # except 内の snippet 取り出しでも raw.decode が例外→内側 except(pass) 到達。
            return bad, "text/plain", 400  # type: ignore[return-value]

        async def _fake_gather(*tasks, **kwargs):
            return [(bad, "text/plain", 400)]

        with patch("common.utils.webread_utils._fetch", new=_fake_fetch), \
             patch("common.utils.webread_utils.asyncio.gather", new=_fake_gather):
            items = _run(self.mod.read_urls(["https://example.com/a"]))
        self.assertEqual(items[0]["error"], "HTTP 400")  # snippet は付かない（内側 except で pass）

    # [T08-04-07] _pick_main_block: div比較で更新しない枝（n <= best_len）到達
    def test_07_pick_main_block_div_no_update_branch(self):
        # article/main が無いので div 最大探索へ
        raw = (
            "<html><body>"
            "<div>" + ("A" * 300) + "</div>"   # best_len 更新 (True)
            "<div>" + ("B" * 10) + "</div>"    # 更新しない (False)
            "</body></html>"
        ).encode("utf-8")
        doc = self.mod._parse_html(raw)
        self.assertIsNotNone(doc)
        out = self.mod._pick_main_block(doc)
        self.assertEqual(out, "A" * 300)

    # [T08-04-08] _fetch: トリムしない枝（len(raw) <= max_bytes）到達
    def test_08_fetch_no_trim_when_under_limit(self):
        class _Resp:
            def __init__(self):
                self.headers = {"Content-Type": "text/plain"}
                self.status = 200

            async def read(self):
                return b"HELLO"  # len=5

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

        class _Session:
            def get(self, url, headers=None, timeout=None, allow_redirects=True):
                return _Resp()

        async def _call():
            # max_bytes=10 で len(raw)=5 -> if条件 False
            raw, ctype, status = await self.mod._fetch(_Session(), "https://example.com", 10, None)
            return raw, ctype, status

        raw, ctype, status = _run(_call())
        self.assertEqual(raw, b"HELLO")  # トリムされない
        self.assertEqual(ctype, "text/plain")
        self.assertEqual(status, 200)


if __name__ == "__main__":
    mapping = {
        "test_01_pick_main_block_article_return": ("COMMON-UTILS:T08-04-01", "_pick_main_block: article/main len>200 で return"),
        "test_02_fetch_trims_max_bytes": ("COMMON-UTILS:T08-04-02", "_fetch: max_bytes トリム + 正常戻り"),
        "test_03_parse_html_double_fail_returns_none": ("COMMON-UTILS:T08-04-03", "_parse_html: 2段階失敗で None"),
        "test_04_collect_images_src_empty_is_skipped": ("COMMON-UTILS:T08-04-04", "_collect_images: src=='' は skip"),
        "test_05_collect_images_base_url_no_match_and_limit_break": ("COMMON-UTILS:T08-04-05", "_collect_images: base_url 不一致 + limit break"),
        "test_06_read_urls_snippet_decode_raises_inner_except": ("COMMON-UTILS:T08-04-06", "read_urls: snippet decode 例外で内側 except 到達"),
        "test_07_pick_main_block_div_no_update_branch": ("COMMON-UTILS:T08-04-07", "_pick_main_block: div比較で更新しない枝"),
        "test_08_fetch_no_trim_when_under_limit": ("COMMON-UTILS:T08-04-08", "_fetch: トリムしない枝（len<=max_bytes）"),
    }
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(WebReadUtilsUncoveredBranchTest)
    run_unittest_suite("COMMON-UTILS:T08-04 common/utils/webread_utils uncovered", suite, mapping)
