
# websearch_utils_test.py
# DuckDuckGo を使った実ネットワーク疎通テスト（CLI 実行用）
#
# 使い方:
#   python websearch_utils_test.py --query "2025年8月26日 天気予報"
#   python websearch_utils_test.py --multi "duckduckgo-search python" "ddgs api" -k 5 -r 30
#   python websearch_utils_test.py  # 既定クエリで実行
#
# 終了コード:
#   0 = OK / それ以外 = 失敗

from pathlib import Path
import sys
sys.path.append(str(Path(__file__).resolve().parents[2]))  # プロジェクトルートを追加

import sys
import argparse
import asyncio
from typing import List
import websearch_utils as wsu


def _print_header(title: str) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


async def _run_single(query: str, top: int, recency_days: int | None, lang: str, timeout: int) -> int:
    _print_header(f"[Single] query='{query}' top={top} recency_days={recency_days} lang={lang} timeout={timeout}")
    try:
        results = await wsu.search_web(query, top_result=top, recency_days=recency_days, lang=lang, timeout=timeout)
    except Exception as e:
        print(f"❌ search_web で例外: {e}")
        return 2

    if not isinstance(results, list):
        print("❌ 結果が list ではありません。")
        return 2

    if len(results) == 0:
        print("⚠️ 結果が 0 件です（ネットワークや環境によっては一時的に起きます）。")
        # 続行するが、後続で再度判定
    else:
        print(f"✅ ヒット {len(results)} 件")
        print(wsu.format_results_as_markdown(results))

    # 形の検査（空でも一応キー存在チェックはスキップ）
    if results:
        keys = set(results[0].keys())
        required = {"title", "url", "snippet", "source"}
        if not required.issubset(keys):
            print(f"❌ 必須キーが欠けています: have={keys}, need={required}")
            return 2

    # 成功（ヒット 0 件は警告として 0 で返す）
    return 0


async def _run_multi(queries: List[str], top: int, recency_days: int | None, lang: str, timeout: int) -> int:
    _print_header(f"[Multi] queries={queries} top={top} recency_days={recency_days} lang={lang} timeout={timeout}")
    try:
        results = await wsu.search_web(queries, top_result=top, recency_days=recency_days, lang=lang, timeout=timeout)
    except Exception as e:
        print(f"❌ search_web で例外: {e}")
        return 2

    if not isinstance(results, list):
        print("❌ 結果が list ではありません。")
        return 2

    if len(results) == 0:
        print("⚠️ 結果が 0 件です（ネットワークや環境によっては一時的に起きます）。")
    else:
        print(f"✅ ヒット {len(results)} 件（重複URLは集約済みのはず）")
        print(wsu.format_results_as_markdown(results))

    # 形の検査
    if results:
        keys = set(results[0].keys())
        required = {"title", "url", "snippet", "source"}
        if not required.issubset(keys):
            print(f"❌ 必須キーが欠けています: have={keys}, need={required}")
            return 2

    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="websearch_utils の実ネットワーク疎通テスト")
    parser.add_argument("--query", "-q", type=str, default="2025年8月26日 天気予報", help="単一クエリ文字列")
    parser.add_argument("--multi", "-m", nargs="*", help="複数クエリ（スペース区切りで複数指定）")
    parser.add_argument("--top", "-k", type=int, default=5, help="top_result 件数（既定: 5）")
    parser.add_argument("--recency-days", "-r", type=int, default=30, help="recency_days（例: 30/90/365）")
    parser.add_argument("--lang", "-l", type=str,  help="検索言語（既定: None）")
    parser.add_argument("--timeout", "-t", type=int, default=10, help="タイムアウト秒（既定: 10）")

    args = parser.parse_args(argv)

    # 依存確認（duckduckgo-search）
    try:
        import duckduckgo_search  # noqa: F401
    except Exception:
        print("❌ duckduckgo-search が見つかりません。`pip install duckduckgo-search>=5.3.1` を実行してください。")
        return 2

    # 実行
    code = 0
    if args.multi:
        code = asyncio.run(_run_multi(args.multi, args.top, args.recency_days, args.lang, args.timeout))
    else:
        code = asyncio.run(_run_single(args.query, args.top, args.recency_days, args.lang, args.timeout))

    # 0=成功/警告含む、2=失敗
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
