# common/utils/webread_utils.py
from __future__ import annotations
import re
import asyncio
import aiohttp
from typing import List, Dict, Any, Optional, Tuple
from lxml import html as lxml_html

UA = "AIChaBoWebReader/1.0 (+https://github.com/mayusaki3/AIChaBo)"

_DEFAULT_TIMEOUT = aiohttp.ClientTimeout(total=20)

def _clean_whitespace(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())

def _guess_published(doc: lxml_html.HtmlElement) -> Optional[str]:
    # 代表的な公開日メタを拾う
    X = doc.xpath
    cands = []
    cands += X("//meta[@property='article:published_time']/@content")
    cands += X("//meta[@name='pubdate']/@content")
    cands += X("//meta[@name='date']/@content")
    cands += X("//time/@datetime")
    cands += [t for t in X("//time/text()")]
    for v in cands:
        v = _clean_whitespace(v)
        if re.search(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}", v):
            return v
    return None

def _extract_title(doc: lxml_html.HtmlElement) -> str:
    X = doc.xpath
    for xp in [
        "string(//meta[@property='og:title']/@content)",
        "string(//meta[@name='twitter:title']/@content)",
        "string(//title)"
    ]:
        t = _clean_whitespace(doc.xpath(xp))
        if t:
            return t
    return ""

def _drop_noise(doc: lxml_html.HtmlElement) -> None:
    for xp in ["//script", "//style", "//noscript", "//header", "//footer", "//nav", "//aside", "//form"]:
        for n in doc.xpath(xp):
            n.drop_tree()

def _pick_main_block(doc: lxml_html.HtmlElement) -> str:
    # article/main を優先、次にテキスト量の大きいdivを採用
    for xp in ["//article", "//main", "//div[@id='main']", "//section[@id='main']"]:
        nodes = doc.xpath(xp)
        if nodes:
            text = _clean_whitespace(" ".join(nodes[0].itertext()))
            if len(text) > 200:
                return text
    # 最大テキスト量のdiv
    best, best_len = "", 0
    for div in doc.xpath("//div"):
        text = _clean_whitespace(" ".join(div.itertext()))
        n = len(text)
        if n > best_len:
            best, best_len = text, n
    return best

def _summarize(text: str, max_chars: int = 800) -> str:
    text = _clean_whitespace(text)
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1] + "…"

async def _fetch(session: aiohttp.ClientSession, url: str, max_bytes: int) -> Tuple[bytes, str, int]:
    async with session.get(url, headers={"User-Agent": UA}, timeout=_DEFAULT_TIMEOUT, allow_redirects=True) as resp:
        ctype = resp.headers.get("Content-Type", "")
        raw = await resp.read()
        if max_bytes and len(raw) > max_bytes:
            raw = raw[:max_bytes]
        return raw, ctype, resp.status

def _parse_html(raw: bytes) -> Optional[lxml_html.HtmlElement]:
    try:
        return lxml_html.fromstring(raw)
    except Exception:
        try:
            txt = raw.decode("utf-8", errors="ignore")
            return lxml_html.fromstring(txt.encode("utf-8"))
        except Exception:
            return None

def _collect_images(doc: lxml_html.HtmlElement, base_url: str, limit: int = 6) -> List[str]:
    imgs = []
    for img in doc.xpath("//img[@src]"):
        src = img.get("src")
        if not src:
            continue
        if src.startswith("//"):
            src = "https:" + src
        elif src.startswith("/"):
            # 雑だが十分：プロトコル/ホストを切り出し
            m = re.match(r"^https?://[^/]+", base_url)
            if m:
                src = m.group(0) + src
        imgs.append(src)
        if len(imgs) >= limit:
            break
    return imgs

async def read_urls(
    urls: List[str],
    *,
    max_bytes: int = 1_500_000,
    max_chars: int = 20_000,
    follow_pdfs: bool = True,
    extract_images: bool = True,
    analyze_images: bool = False,  # TODO: 未実装、解析自体は別ツールで
    language_hint: Optional[str] = None,
    require_citations: bool = True,
) -> List[Dict[str, Any]]:
    """各URLを取得して {title, url, published, summary, images, is_pdf, note} を返す。"""
    results: List[Dict[str, Any]] = []
    timeout = _DEFAULT_TIMEOUT
    conn = aiohttp.TCPConnector(limit=6, ssl=False)
    async with aiohttp.ClientSession(timeout=timeout, connector=conn) as session:
        tasks = []
        for u in urls[:8]:
            tasks.append(_fetch(session, u, max_bytes))
        fetched = await asyncio.gather(*tasks, return_exceptions=True)

    for u, item in zip(urls[:8], fetched):
        if isinstance(item, Exception):
            results.append({"url": u, "error": str(item)})
            continue
        raw, ctype, status = item
        if status >= 400:
            results.append({"url": u, "error": f"HTTP {status}"})
            continue
        is_pdf = ("application/pdf" in ctype.lower()) or u.lower().endswith(".pdf")
        if is_pdf:
            note = "PDF検出（本文抽出は未実装）"
            results.append({
                "url": u, "is_pdf": True, "title": "", "published": None,
                "summary": "", "images": [], "note": note
            })
            continue

        doc = _parse_html(raw)
        if not doc:
            results.append({"url": u, "error": "HTML解析に失敗"})
            continue

        _drop_noise(doc)
        title = _extract_title(doc)
        published = _guess_published(doc)
        main = _pick_main_block(doc)
        if not main:
            main = _clean_whitespace(" ".join(doc.itertext()))
        if max_chars and len(main) > max_chars:
            main = main[: max_chars] + "…"

        images = _collect_images(doc, u) if extract_images else []

        summary = _summarize(main, max_chars=min(800, max_chars))
        results.append({
            "url": u,
            "title": title,
            "published": published,
            "summary": summary,
            "images": images,
            "is_pdf": False
        })

    return results

def format_read_results_for_llm(items: List[Dict[str, Any]], require_citations: bool = True) -> str:
    """LLMへ渡すための簡潔なマークダウン（番号付き引用）"""
    lines = []
    for i, it in enumerate(items, 1):
        if "error" in it:
            lines.append(f"{i}. **(取得失敗)** {it.get('url')} — {it['error']}")
            continue
        mark = f"{i}. **{_clean_whitespace(it.get('title') or '(無題)')}**"
        mark += f"\n   {_clean_whitespace(it['url'])}"
        if it.get("published"):
            mark += f"\n   Published: {it['published']}"
        if it.get("summary"):
            mark += f"\n   Summary: {it['summary']}"
        if it.get("is_pdf"):
            mark += f"\n   Note: PDF detected."
        if it.get("images"):
            imgs = ", ".join(it["images"][:3])
            mark += f"\n   Images: {imgs}"
        lines.append(mark)
    if require_citations and items:
        # 末尾にシンプルな引用注記
        lines.append("\nSources: " + " ".join(f"[{i}] {it.get('url')}" for i, it in enumerate(items, 1)))
    return "\n".join(lines)
