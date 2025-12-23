# -*- coding: utf-8 -*-
"""
T08-04 : Sharing Session (Branch Coverage)
対象: common.chat.sharing

目的:
- sharing.py の分岐網羅率（branch coverage）を上げるためのテスト。
- 仕様テスト（T08-01〜03）では踏みにくいフォールバック経路を安全に通す。
"""

import unittest
from typing import Dict, Tuple

from tests._report import run_unittest_suite


class SharingBranchCoverageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from common.chat import sharing as S  # type: ignore
        cls.mod = S

    # [T08-04-01] export: 空dictでも例外にならず str を返す
    def test_01_export_empty_dict(self):
        out = self.mod.export_session({})  # type: ignore[attr-defined]
        self.assertIsInstance(out, str)

    # [T08-04-02] export: 非dict入力でも例外にならず str を返す
    def test_02_export_non_dict(self):
        out1 = self.mod.export_session([])      # type: ignore[arg-type,attr-defined]
        out2 = self.mod.export_session("x")     # type: ignore[arg-type,attr-defined]
        self.assertIsInstance(out1, str)
        self.assertIsInstance(out2, str)

    # [T08-04-03] import: unknown version を含む入力でも dict として復元される
    def test_03_import_unknown_version(self):
        raw = {
            "version": 999,
            "messages": [{"role": "user", "content": "hi"}],
            "provider": "openai",
            "model": "gpt-4o",
        }
        out = self.mod.import_session(raw)  # type: ignore[arg-type,attr-defined]
        self.assertIsInstance(out, dict)
        self.assertIn("messages", out)

    # [T08-04-04] import: messages が list 以外でも安全に list へ補正される
    def test_04_import_messages_not_list(self):
        raw = {
            "version": 1,
            "messages": "invalid",
            "provider": "openai",
            "model": "gpt-4o",
        }
        out = self.mod.import_session(raw)  # type: ignore[arg-type,attr-defined]
        self.assertIsInstance(out, dict)
        self.assertIsInstance(out.get("messages"), list)

    # [T08-04-05] import: legacy 形式で messages 欠落でも messages を補完する
    def test_05_legacy_messages_missing(self):
        raw = {
            "id": "legacy",
            "provider": "openai",
            "model": "gpt-4o",
        }
        out = self.mod.import_session(raw)  # type: ignore[arg-type,attr-defined]
        self.assertIsInstance(out, dict)
        self.assertIn("messages", out)
        self.assertIsInstance(out["messages"], list)

    # [T08-04-06] share_to_guild: no-op 経路（内部保存が未実装でも例外なし）
    def test_06_share_to_guild_noop(self):
        # hasattr(manager, "share_to_guild") == False を確実に踏む
        from unittest.mock import patch

        class DummyNoShare:
            pass

        with patch("common.chat.sharing.SSM", return_value=DummyNoShare()):
            self.mod.share_to_guild(guild_id=1, session={"id": "s1"})  # type: ignore[attr-defined]

    # [T08-04-07] share_to_guild: 実装がある場合は呼ばれる（hasattr True 側）
    def test_07_share_to_guild_calls_impl(self):
        from unittest.mock import patch, MagicMock

        class DummyHasShare:
            def __init__(self):
               self.share_to_guild = MagicMock()

        dummy = DummyHasShare()
        with patch("common.chat.sharing.SSM", return_value=dummy):
            self.mod.share_to_guild(guild_id=123, session={"id": "s1", "messages": []})  # type: ignore[attr-defined]
        dummy.share_to_guild.assert_called_once()
        _, kwargs = dummy.share_to_guild.call_args
        self.assertEqual(kwargs.get("guild_id"), 123)

    # [T08-04-08] import: int 変換例外でも落ちずにフォールバック（_to_int_or_none 例外側）
    def test_08_import_version_int_cast_exception(self):
        raw = {
            "version": {"x": 1},  # int(...) が TypeError になりやすい
            "messages": [],
        }
        out = self.mod.import_session(raw)  # type: ignore[arg-type,attr-defined]
        self.assertIsInstance(out, dict)
        self.assertIsInstance(out.get("messages"), list)

    # [T08-04-09] import: provider/model/meta 型不正は枝刈り（sanitize 分岐）
    def test_09_import_sanitize_type_filters(self):
        raw = {
            "version": 1,
            "messages": [],
            "provider": 123,       # str 以外 → 落ちる想定
            "model": ["gpt-4o"],   # str 以外 → 落ちる想定
            "meta": "nope",        # dict 以外 → 落ちる想定
        }
        out = self.mod.import_session(raw)  # type: ignore[arg-type,attr-defined]
        self.assertIsInstance(out, dict)
        self.assertNotIn("provider", out)
        self.assertNotIn("model", out)
        self.assertNotIn("meta", out)

    # [T08-04-10] sanitize: messages 非list → None（_sanitize_import_dict ガード）
    def test_10_sanitize_messages_not_list(self):
        out = self.mod._sanitize_import_dict({"messages": "x"})  # type: ignore[arg-type,attr-defined]
        self.assertIsNone(out)

    # [T08-04-11] sanitize: provider/model/meta 型不正は落とす（枝刈り）
    def test_11_sanitize_type_filters(self):
        raw = {
            "id": "s1",
            "ts": 1,
            "messages": [],
            "provider": 123,
            "model": ["x"],
            "meta": "nope",
        }
        out = self.mod._sanitize_import_dict(raw)  # type: ignore[arg-type,attr-defined]
        self.assertIsInstance(out, dict)
        self.assertNotIn("provider", out)
        self.assertNotIn("model", out)
        self.assertNotIn("meta", out)

    # [T08-04-12] to_int: int 変換例外は None（_to_int_or_none except 側）
    def test_12_to_int_or_none_exception(self):
        out = self.mod._to_int_or_none({"x": 1})  # type: ignore[attr-defined]
        self.assertIsNone(out)

    # [T08-04-13] normalize: 非dict入力は空正規化（_normalize_legacy_session 早期 return）
    def test_13_normalize_legacy_non_dict(self):
        ns = self.mod._normalize_legacy_session("x")  # type: ignore[arg-type,attr-defined]
        self.assertIsNone(ns.session_id)
        self.assertIsInstance(ns.messages, list)

    # [T08-04-14] normalize: v0 + session ネスト分岐（version==0 かつ session dict）
    def test_14_normalize_legacy_v0_nested_session(self):
        obj = {
            "version": 0,
            "session": {
                "id": "s0",
                "timestamp": "2",
                "provider": 123,
                "model": ["x"],
                "history": "bad",
                "meta": "nope",
            },
        }
        ns = self.mod._normalize_legacy_session(obj)  # type: ignore[attr-defined]
        self.assertEqual(ns.session_id, "s0")
        self.assertEqual(ns.ts, 2)
        self.assertIsNone(ns.provider)
        self.assertIsNone(ns.model)
        self.assertEqual(ns.messages, [])
        self.assertEqual(ns.meta, {})

    # [T08-04-15] share: _share_to_server_impl の hasattr False 側を確実に踏む
    def test_15_share_to_server_impl_hasattr_false(self):
        from unittest.mock import patch

        class DummyNoShare:
            pass

        with patch("common.chat.sharing.SSM", return_value=DummyNoShare()):
            self.mod._share_to_server_impl(  # type: ignore[attr-defined]
                guild_id=1,
                session={"id": "s1", "messages": []},
            )

    # [T08-04-16] normalize: base が dict でない場合に base={} へ補正（line 64）
    def test_16_normalize_base_not_dict_branch(self):
        # ver==0 かつ obj.get("session") は dict を返すが、obj["session"] は非dictを返すように細工する
        class WeirdDict(dict):
            def get(self, key, default=None):
                if key == "session":
                    return {}  # isinstance(obj.get("session"), dict) を True にする
                return super().get(key, default)

            def __getitem__(self, key):
                if key == "session":
                    return "not-a-dict"  # base を非dictにする
                return super().__getitem__(key)

        obj = WeirdDict({"version": 0})
        ns = self.mod._normalize_legacy_session(obj)  # type: ignore[attr-defined]
        self.assertIsNone(ns.session_id)
        self.assertIsInstance(ns.messages, list)

    # [T08-04-17] export/import: meta(dict) を保持（line 101 + line 123）
    def test_17_export_import_meta_preserved(self):
        base = {"id": "s1", "ts": 1, "messages": [], "meta": {"k": "v"}}
        s = self.mod.export_session(base)  # type: ignore[attr-defined]
        out = self.mod.import_session(s)   # type: ignore[attr-defined]
        self.assertIsInstance(out, dict)
        self.assertEqual(out.get("meta"), {"k": "v"})

    # [T08-04-18] sanitize: data が dict 以外 → None（line 107）
    def test_18_sanitize_non_dict_returns_none(self):
        out = self.mod._sanitize_import_dict("x")  # type: ignore[arg-type,attr-defined]
        self.assertIsNone(out)

    # [T08-04-19] import: sanitized is None → 空セッションへフォールバック（line 170）
    def test_19_import_sanitized_none_fallback(self):
        from unittest.mock import patch
        with patch("common.chat.sharing._sanitize_import_dict", return_value=None):
            out = self.mod.import_session({"version": 1, "messages": []})  # type: ignore[arg-type,attr-defined]
        self.assertIsInstance(out, dict)
        self.assertEqual(out.get("messages"), [])


if __name__ == "__main__":
    mapping: Dict[str, Tuple[str, str]] = {
        "test_01_export_empty_dict": (
            "COMMON-CHAT:T08-04-01",
            "export_session: 空dict入力でも例外にならず str を返す",
        ),
        "test_02_export_non_dict": (
            "COMMON-CHAT:T08-04-02",
            "export_session: 非dict入力でも例外にならず str を返す",
        ),
        "test_03_import_unknown_version": (
            "COMMON-CHAT:T08-04-03",
            "import_session: unknown version 入力でも dict として復元される",
        ),
        "test_04_import_messages_not_list": (
            "COMMON-CHAT:T08-04-04",
            "import_session: messages が list 以外でも安全に list 補正される",
        ),
        "test_05_legacy_messages_missing": (
            "COMMON-CHAT:T08-04-05",
            "import_session: legacy 形式で messages 欠落でも messages を補完する",
        ),
        "test_06_share_to_guild_noop": (
            "COMMON-CHAT:T08-04-06",
            "share_to_guild: no-op 経路（内部保存未実装でも例外なし）",
        ),
        "test_07_share_to_guild_calls_impl": (
            "COMMON-CHAT:T08-04-07",
            "share_to_guild: 実装がある場合は呼ばれる（hasattr True 側）",
        ),
        "test_08_import_version_int_cast_exception": (
            "COMMON-CHAT:T08-04-08",
            "import_session: int 変換例外でも落ちずにフォールバック（_to_int_or_none 例外側）",
        ),
        "test_09_import_sanitize_type_filters": (
            "COMMON-CHAT:T08-04-09",
            "import_session: provider/model/meta 型不正は枝刈り（sanitize 分岐）",
        ),
        "test_10_sanitize_messages_not_list": (
            "COMMON-CHAT:T08-04-10",
            "sanitize: messages 非list → None（ガード）",
        ),
        "test_11_sanitize_type_filters": (
            "COMMON-CHAT:T08-04-11",
            "sanitize: provider/model/meta 型不正は落とす（枝刈り）",
        ),
        "test_12_to_int_or_none_exception": (
            "COMMON-CHAT:T08-04-12",
            "_to_int_or_none: int 変換例外は None（except 側）",
        ),
        "test_13_normalize_legacy_non_dict": (
            "COMMON-CHAT:T08-04-13",
            "_normalize_legacy_session: 非dict入力は空正規化（早期return）",
        ),
        "test_14_normalize_legacy_v0_nested_session": (
            "COMMON-CHAT:T08-04-14",
            "_normalize_legacy_session: v0(sessionネスト)分岐",
        ),
        "test_15_share_to_server_impl_hasattr_false": (
            "COMMON-CHAT:T08-04-15",
            "_share_to_server_impl: hasattr False 側",
        ),
        "test_16_normalize_base_not_dict_branch": (
            "COMMON-CHAT:T08-04-16",
            "_normalize_legacy_session: base 非dict → base={} 補正（line 64）",
        ),
        "test_17_export_import_meta_preserved": (
            "COMMON-CHAT:T08-04-17",
            "export/import: meta(dict) を保持（line 101/123）",
        ),
        "test_18_sanitize_non_dict_returns_none": (
            "COMMON-CHAT:T08-04-18",
            "_sanitize_import_dict: data 非dict → None（line 107）",
        ),
        "test_19_import_sanitized_none_fallback": (
            "COMMON-CHAT:T08-04-19",
            "import_session: sanitized None → 空セッション（line 170）",
        ),
    }

    suite = unittest.defaultTestLoader.loadTestsFromTestCase(SharingBranchCoverageTest)
    run_unittest_suite("COMMON-CHAT:T08-04 common/chat/sharing branch", suite, mapping)
