from __future__ import annotations
from typing import List, Dict, Optional, Union, Tuple
from common.actions.action_utils import ddg_timelimit, ddg_region_for_lang

class WebSearchError(Exception):
    pass

# ---- 低レベル: 実検索 ----

# DuckDuckGo検索（duckduckgo-search 依存）。
# - 同期版 DDGS をスレッド実行
# 戻り値: [{title, url, snippet, source}]
async def _search_duckduckgo(query: str, *, top: int, timelimit: Optional[str], lang: Optional[str], region: Optional[str], timeout: int) -> List[Dict]:
    from duckduckgo_search import DDGS  # v5〜v8
    import asyncio
    loop = asyncio.get_running_loop()
    if not region:
        region = ddg_region_for_lang(lang)

    def _sync_search():
        out: List[Dict] = []
        with DDGS() as ddgs:
            try:
                it = ddgs.text(query, max_results=max(1, min(top, 15)), region=region, timelimit=timelimit)
            except TypeError:
                try:
                    it = ddgs.text(query, max_results=max(1, min(top, 15)), region=region)
                except TypeError:
                    it = ddgs.text(query, region=lang)
            for r in it:
                title = (r.get("title") or "").strip()
                url = (r.get("href") or "").strip()
                snippet = (r.get("body") or "").strip()
                if url:
                    out.append({"title": title or url, "url": url, "snippet": snippet, "source": "duckduckgo"})
                if len(out) >= top:
                    break
        return out

    try:
        return await asyncio.wait_for(loop.run_in_executor(None, _sync_search), timeout=timeout)
    except asyncio.TimeoutError as te:
        raise WebSearchError(f"DuckDuckGo 検索がタイムアウトしました（{timeout}s）") from te

# ---- 公開 API ----

# 汎用 Web 検索（duckduckgo-search 専用）
# - queries: 文字列 or クエリ配列（1〜3件想定）。配列なら集約して上位 top_result 件に丸める
# - recency_days: 30 / 90 / 365 / None を 'm' / 'y' に丸めて DDG timelimit に反映
# - 戻り値: [{title, url, snippet, source}, ...]
async def search_web(
    queries: Union[str, List[str]],
    *,
    top_result: int = 5,
    recency_days: Optional[int] = None,
    lang: Optional[str] = None,
    region: Optional[str] = None,
    timeout: int = 15,
) -> List[Dict]:
    # クエリ配列に正規化
    if isinstance(queries, str):
        qs: List[str] = [queries]
    else:
        qs = [q for q in queries if isinstance(q, str) and q.strip()]
    if not qs:
        return []
    qs = qs[:3]

    # 件数をクランプ
    top = max(3, min(top_result, 8))

    # DDG timelimit に変換
    timelimit = ddg_timelimit(recency_days)  # d/w/m/y or None

    # まとめて検索 & 集約（URL 重複排除）
    aggregated: List[Dict] = []
    seen_urls: set[str] = set()

    for q in qs:
        results = await _search_duckduckgo(q, top=top, timelimit=timelimit, lang=lang, region=region, timeout=timeout)

        for r in results:
            url = r.get("url") or ""
            if url and url not in seen_urls:
                seen_urls.add(url)
                aggregated.append(r)
            if len(aggregated) >= top:
                break
        if len(aggregated) >= top:
            break

    return aggregated[:top]

# 検索結果を Discord へ貼りやすい Markdown に整形。
# - require_citations=True のときは URL を必ず表示（※既に表示しているため既定 True）
def format_results_as_markdown(results: List[Dict], *, require_citations: bool = True) -> str:
    if not results:
        return "（該当なし）"

    lines = []
    for i, r in enumerate(results, 1):
        title = r.get("title") or r.get("url") or "No title"
        url = r.get("url") or ""
        snippet = r.get("snippet") or ""
        if require_citations and url:
            lines.append(f"{i}. **{title}**\n   {url}\n   {snippet}")
        else:
            lines.append(f"{i}. **{title}**\n   {snippet}")
    return "\n".join(lines)
