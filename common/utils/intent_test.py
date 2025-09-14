# common/utils/intent_test.py
# intent_test.py — インテントYAMLの簡易テスター（CLI）
#
# 使い方:
#   # デフォルト（weather/ja）
#   python -m common.utils.intent_test "明日の大阪の天気は？"
#
#   # 複数入力
#   python -m common.utils.intent_test "明日の京都の天気" "東京の天気は？"
#
#   # 他インテント / ロケール指定
#   python -m common.utils.intent_test --intent weather --locale ja "明日の名古屋の天気"
#
#   # YAML再読込（ホットリロード）
#   python -m common.utils.intent_test --reload "明日の福岡の天気"
#
# 終了コード:
#   0 = 成功 / (該当なしは "(該当なし)" 表示)
#   2 = 失敗（例外など）
#
# 必要ファイル:
#   common/config/intents/*.yaml, common/config/dictionaries/*.yaml

from __future__ import annotations
import sys
import argparse
from pathlib import Path
from typing import List
from .intent import build_tool_hint_from_config, build_tool_hint_auto, clear_intent_caches

def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Intent YAML loader quick test")
    parser.add_argument("text", nargs="*", help="テストする入力文（スペース区切りで複数可）")
    parser.add_argument("--intent", default="weather", help="インテント名（例: weather）")
    parser.add_argument("--auto", action="store_true", help="インテント自動判定で実行する")
    parser.add_argument("--locale", default="ja", help="ロケール（例: ja）")
    parser.add_argument("--reload", action="store_true", help="YAMLを再読み込み（lru_cacheをクリア）")
    args = parser.parse_args(argv)

    if args.reload:
        clear_intent_caches()

    texts = args.text or ["明日の大阪の天気は？"]
    mode = "auto" if args.auto else args.intent
    print(f"[intent={mode}, locale={args.locale}]")
    for t in texts:
        hint = (build_tool_hint_auto(t, args.locale)
            if args.auto else
            build_tool_hint_from_config(args.intent, t, args.locale))
        print("\n== INPUT ==")
        print(t)
        print("== HINT ==")
        print(hint or "(該当なし)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
