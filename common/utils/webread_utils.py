# common/utils/webread_utils.py
from __future__ import annotations
import re
import asyncio
import aiohttp
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urlparse
from lxml import html as lxml_html

UA = "AIChaBoWebReader/1.0 (+https://github.com/mayusaki3/AIChaBo)"
_DEFAULT_TIMEOUT = aiohttp.ClientTimeout(total=20)
LLM_AUTH_HOSTS = {
    "api.openai.com","oai.ai","api.anthropic.com",
    "generativelanguage.googleapis.com","ai.googleusercontent.com",
    "openai.azure.com","models.inference.ai.azure.com",
}
GITHUB_HOSTS = {"github.com","api.github.com","raw.githubusercontent.com"}
_SECRET_PATS = [r"sk-[A-Za-z0-9]{20,}", r"anthropic-[A-Za-z0-9_\\-]{20,}", r"AIza[0-9A-Za-z_\\-]{20,}"]
def redact(s: str) -> str:
    if not isinstance(s,str) or not s: return s
    import re as _re
    out = s
    for pat in _SECRET_PATS:
       out = _re.sub(pat, lambda m: m.group(0)[:4]+"…"+m.group(0)[-4:], out)
    return out

def _clean_whitespace(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())

def _filename_from_url(u: str) -> str:
    m = re.search(r"/([^/?#]+)$", u or "")
    return m.group(1) if m else ""

def _is_html_ctype(ctype: str) -> bool:
    s = (ctype or "").lower()
    return ("text/html" in s) or ("application/xhtml" in s)

def _is_text_like(ctype: str, url: str) -> bool:
    s = (ctype or "").lower()
    if s.startswith("text/"):
        return True
    if any(k in s for k in ["json", "javascript", "xml", "x-python", "x-script", "csv", "yaml", "toml"]):
        return True
    # URL拡張子で推定（Discord CDN は octet-stream になることがある）
    path = (url or "").lower().split("?")[0]
    for ext in (".py",".txt",".md",".json",".csv",".yml",".yaml",".toml",".ini",".cfg",".log",".rst"):
        if path.endswith(ext):
            return True
    return False

def _decode_text(raw: bytes) -> str:
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        try:
            return raw.decode("cp932")
        except UnicodeDecodeError:
            return raw.decode("utf-8", errors="replace")

def _summarize_code(txt: str, *, max_chars: int = 1200, max_lines: int = 60) -> str:
    # コード/プレーンテキストは整形せず先頭を抜粋
    out, total = [], 0
    for line in (txt or "").splitlines():
        ln = line.rstrip("\r")
        n = len(ln) + 1
        if (total + n > max_chars) or (len(out) >= max_lines):
            break
        out.append(ln)
        total += n
    body = "\n".join(out)
    if len(body) < len(txt):
        # コードブロックは正しく閉じ、補足はブロック外に置く
        return "```text\n" + body + "\n```\n（長文のため一部省略）"
    return "```text\n" + body + "\n```"

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

def _build_request_headers(url: str, extra: Optional[Dict[str, str]]) -> Dict[str, str]:
    """
    汎用I/O層：特定サービス(GitHub等)の暗黙ヘッダは付与しない。
    認証・特殊ヘッダは呼び出し元（=各プラグイン）で明示的に指定する。
    """
    base = {"User-Agent": UA}
    host = (urlparse(url).hostname or "").lower()
    if extra:
        for k, v in extra.items():
            if not v: continue
            if k.lower()=="authorization":
                # GitHubは常に拒否（公開のみ運用）、LLM先のみ許可
                if host in GITHUB_HOSTS: 
                    continue
                if host in LLM_AUTH_HOSTS:
                    base["Authorization"] = v
            else:
                base[k] = v
    return base

async def _fetch(session: aiohttp.ClientSession, url: str, max_bytes: int, req_headers: Optional[Dict[str, str]] = None) -> Tuple[bytes, str, int]:
    async with session.get(url, headers=_build_request_headers(url, req_headers), timeout=_DEFAULT_TIMEOUT, allow_redirects=True) as resp:
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
    headers: Optional[Dict[str, str]] = None,
) -> List[Dict[str, Any]]:
    """各URLを取得して {title, url, published, summary, images, is_pdf, note} を返す。"""
    results: List[Dict[str, Any]] = []
    timeout = _DEFAULT_TIMEOUT
    conn = aiohttp.TCPConnector(limit=6, ssl=False)
    async with aiohttp.ClientSession(timeout=timeout, connector=conn) as session:
        tasks = []
        for u in urls[:8]:
            tasks.append(_fetch(session, u, max_bytes, headers))
        fetched = await asyncio.gather(*tasks, return_exceptions=True)

    for u, item in zip(urls[:8], fetched):
        if isinstance(item, Exception):
            results.append({"url": u, "error": str(item)})
            continue
        raw, ctype, status = item
        # 4xx/5xx 時の詳細メッセージ取り出し（汎用）
        if status >= 400:
            note = f"HTTP {status}"
            # 可能なら JSON を軽く読んで代表的なエラーフィールドを拾う
            try:
                import json as _json
                payload = _json.loads(raw.decode("utf-8", errors="ignore"))
                # よくあるキーを優先順で探索
                for key in ("message", "error", "detail", "error_description", "title"):
                    if isinstance(payload, dict) and payload.get(key):
                        note = f"{note} — {redact(str(payload.get(key))[:300])}"
                        break
            except Exception:
                # JSONでない場合は、先頭数百文字だけ拾う
                try:
                    snippet = redact(raw.decode("utf-8", errors="ignore")[:300])
                    snippet = " ".join(snippet.split())
                    if snippet:
                        note = f"{note} — {snippet}"
                except Exception:
                    pass
            results.append({"url": u, "error": note})
            continue
        is_pdf = ("application/pdf" in ctype.lower()) or u.lower().endswith(".pdf")
        if is_pdf:
            note = "PDF検出（本文抽出は未実装）"
            results.append({
                "url": u, "is_pdf": True, "title": "", "published": None,
                "summary": "", "images": [], "note": note
            })
            continue

        # ---- HTML 以外のテキスト/コードを先に処理 ----
        if not _is_html_ctype(ctype) and _is_text_like(ctype, u):
            txt = _decode_text(raw)
            title = _filename_from_url(u) or "(text)"
            summary = _summarize_code(txt, max_chars=min(1200, max_chars))
            results.append({
                "url": u,
                "title": title,
                "published": None,
                "summary": summary,
                "raw": txt,
                "images": [],
                "is_pdf": False
            })
            continue

        # ---- HTML とみなして解析 ----
        doc = _parse_html(raw)
        if not doc:
            # 非HTML・非テキスト（バイナリ等）は諦める
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
            "text": main,
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
