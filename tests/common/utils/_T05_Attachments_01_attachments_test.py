# -*- coding: utf-8 -*-
"""
COMMON-UTILS:T05 : attachments

対象: common.utils.attachments

目的:
- build_attachment: content_type 指定 or filename 推測により is_image 判定される
- split_attachments: is_image に応じて画像/非画像へ分割される
- render_append_block: 画像/ファイルの出力形式が仕様どおり（空なら空文字、filename None は "file"）

テスト番号:
- COMMON-UTILS:T05-01-01 ...（T05=attachments, 01=テストコード, 01..=ケース）

実行:
- python -m tests.common.utils.T05_Attachments_01_attachments_test
"""

import unittest
from typing import Dict, Tuple

from tests._report import run_unittest_suite


class AttachmentsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from common.utils import attachments as mod  # type: ignore
        cls.mod = mod

    # [COMMON-UTILS:T05-01-01] build_attachment: content_type 指定が優先され is_image 判定される
    def test_01_build_attachment_content_type_overrides(self):
        a = self.mod.build_attachment(
            "https://example.com/x",
            filename="x.bin",
            content_type="image/png",
        )
        self.assertEqual(a.url, "https://example.com/x")
        self.assertEqual(a.filename, "x.bin")
        self.assertEqual(a.content_type, "image/png")
        self.assertTrue(a.is_image)

    # [COMMON-UTILS:T05-01-02] build_attachment: filename から content_type 推測され is_image 判定される
    def test_02_build_attachment_guess_from_filename(self):
        a = self.mod.build_attachment("https://example.com/a.png", filename="a.png")
        # mimetypes に依存するが、png は通常 image/png
        self.assertTrue((a.content_type or "").startswith("image/"))
        self.assertTrue(a.is_image)

    # [COMMON-UTILS:T05-01-03] build_attachment: filename/content_type が無い場合は非画像
    def test_03_build_attachment_no_filename_no_content_type(self):
        a = self.mod.build_attachment("https://example.com/unknown")
        self.assertIsNone(a.filename)
        self.assertIsNone(a.content_type)
        self.assertFalse(a.is_image)

    # [COMMON-UTILS:T05-01-04] split_attachments: is_image で分割
    def test_04_split_attachments(self):
        img = self.mod.build_attachment("u1", filename="a.jpg")
        doc = self.mod.build_attachment("u2", filename="b.pdf", content_type="application/pdf")
        imgs, docs = self.mod.split_attachments([img, doc])
        self.assertEqual(imgs, [img])
        self.assertEqual(docs, [doc])

    # [COMMON-UTILS:T05-01-05] render_append_block: imgs のみ
    def test_05_render_imgs_only(self):
        img1 = self.mod.build_attachment("https://example.com/1.png", filename="1.png")
        img2 = self.mod.build_attachment("https://example.com/2.png", filename="2.png")
        s = self.mod.render_append_block([img1, img2], [])
        self.assertIn("[添付画像]", s)
        self.assertIn("- https://example.com/1.png", s)
        self.assertIn("- https://example.com/2.png", s)
        self.assertNotIn("[添付ファイル]", s)

    # [COMMON-UTILS:T05-01-06] render_append_block: docs のみ（filename あり）
    def test_06_render_docs_only(self):
        doc = self.mod.build_attachment("https://example.com/a.pdf", filename="a.pdf", content_type="application/pdf")
        s = self.mod.render_append_block([], [doc])
        self.assertIn("[添付ファイル]", s)
        self.assertIn("- a.pdf: https://example.com/a.pdf", s)
        self.assertNotIn("[添付画像]", s)

    # [COMMON-UTILS:T05-01-07] render_append_block: docs の filename None は "file"
    def test_07_render_docs_filename_none_uses_file_literal(self):
        # filename=None を明示しても content_type 推測はしない（filenameが無いのでNone）
        doc = self.mod.build_attachment("https://example.com/blob", filename=None, content_type="application/octet-stream")
        s = self.mod.render_append_block([], [doc])
        self.assertIn("[添付ファイル]", s)
        self.assertIn("- file: https://example.com/blob", s)

    # [COMMON-UTILS:T05-01-08] render_append_block: imgs + docs は空行2つで結合される
    def test_08_render_imgs_and_docs_join_format(self):
        img = self.mod.build_attachment("https://example.com/1.png", filename="1.png")
        doc = self.mod.build_attachment("https://example.com/a.pdf", filename="a.pdf", content_type="application/pdf")
        s = self.mod.render_append_block([img], [doc])
        # 先頭に "\n\n" が付く仕様
        self.assertTrue(s.startswith("\n\n"))
        self.assertIn("[添付画像]\n- https://example.com/1.png", s)
        self.assertIn("[添付ファイル]\n- a.pdf: https://example.com/a.pdf", s)

    # [COMMON-UTILS:T05-01-09] render_append_block: 両方空なら空文字
    def test_09_render_empty_returns_empty_string(self):
        s = self.mod.render_append_block([], [])
        self.assertEqual(s, "")


if __name__ == "__main__":
    mapping: Dict[str, Tuple[str, str]] = {
        "test_01_build_attachment_content_type_overrides": ("COMMON-UTILS:T05-01-01", "build_attachment: content_type 優先"),
        "test_02_build_attachment_guess_from_filename": ("COMMON-UTILS:T05-01-02", "build_attachment: filename 推測"),
        "test_03_build_attachment_no_filename_no_content_type": ("COMMON-UTILS:T05-01-03", "build_attachment: 推測不可は非画像"),
        "test_04_split_attachments": ("COMMON-UTILS:T05-01-04", "split_attachments: is_image で分割"),
        "test_05_render_imgs_only": ("COMMON-UTILS:T05-01-05", "render_append_block: imgsのみ"),
        "test_06_render_docs_only": ("COMMON-UTILS:T05-01-06", "render_append_block: docsのみ"),
        "test_07_render_docs_filename_none_uses_file_literal": ("COMMON-UTILS:T05-01-07", "render_append_block: filename None は file"),
        "test_08_render_imgs_and_docs_join_format": ("COMMON-UTILS:T05-01-08", "render_append_block: imgs+docs 結合形式"),
        "test_09_render_empty_returns_empty_string": ("COMMON-UTILS:T05-01-09", "render_append_block: 空は空文字"),
    }
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(AttachmentsTest)
    run_unittest_suite("COMMON-UTILS:T05 common/utils/attachments", suite, mapping)
