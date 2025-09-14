# common/utils/prefetch.py
from __future__ import annotations
from typing import List, Tuple
from common.utils.webread_utils import read_urls, format_read_results_for_llm

async def prefetch_doc_summaries(
    urls: List[str],
    *,
    max_chars: int = 12000,
    max_bytes: int = 1_500_000,
    language_hint: str = "ja",
) -> Tuple[str, Tuple[str, ...]]:
    """非画像添付のURLを読み取り、LLM向けに整形した要約文字列と署名(sig)を返す。"""
    urls = [u for u in (urls or []) if u]
    if not urls:
        return "", tuple()
    items = await read_urls(
        urls,
        max_bytes=max_bytes,
        max_chars=max_chars,
        follow_pdfs=True,
        extract_images=False,
        analyze_images=False,
        language_hint=language_hint,
        require_citations=False,
    )
    formatted = format_read_results_for_llm(items, require_citations=False)
    sig = tuple(urls)[:8]
    return formatted, sig
