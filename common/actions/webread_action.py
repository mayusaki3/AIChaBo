from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse
import json

from common.plugins.dispatcher import try_handle_by_plugin
from common.plugins.base import ReadRequest, ReadResponse, PluginResult
from common.utils.webread_utils import read_urls, format_read_results_for_llm

@dataclass
class WebReadAction:
    tool: str
    urls: List[str]
    version: str = "1"
    # 任意HTTPヘッダ（将来の認証/API用・後方互換のためオプショナル）
    headers: Optional[Dict[str, str]] = None
    # 省略可パラメータ（将来の拡張向け。ひな形では未使用でもOK）
    follow_links: bool = False
    max_pages: int = 1
    require_citations: bool = True
    lang: Optional[str] = None
    region: Optional[str] = None
    # LLM からのテンプレメッセージ（任意）
    success_message: Optional[str] = None
    failure_message: Optional[str] = None

    @staticmethod
    def parse(text: str) -> Optional["WebReadAction"]:
        try:
            obj = json.loads(text)
            t = str(obj.get("tool", "")).replace("_", ".")
            if t != "web.read":
                return None
            urls_field = obj.get("urls") or obj.get("url") or []
            if isinstance(urls_field, str):
                urls = [urls_field]
            elif isinstance(urls_field, list):
                urls = [str(u) for u in urls_field if u]
            else:
                urls = []
            # 正規化 + 検証 (http/https のみ) + 重複排除
            clean: List[str] = []
            for u in urls:
                try:
                    s = u.strip()
                    p = urlparse(s)
                    if p.scheme not in ("http", "https"):
                        continue
                    clean.append(s)
                except Exception:
                    continue
            # preserve order dedupe
            seen = set()
            urls = [x for x in clean if not (x in seen or seen.add(x))]
            if not urls:
                return None

            # 任意ヘッダ（dict想定・不正なら無視）
            headers = obj.get("headers")
            if not isinstance(headers, dict):
                headers = None

            return WebReadAction(
                tool="web.read",
                urls=urls,
                version=str(obj.get("version", "1")),
                follow_links=bool(obj.get("follow_links", False)),
                max_pages=int(obj.get("max_pages", 1)),
                require_citations=bool(obj.get("require_citations", True)),
                lang=obj.get("lang"),
                region=obj.get("region"),
                success_message=obj.get("success_message"),
                failure_message=obj.get("failure_message"),
                headers=headers,
            )
        except Exception:
            return None

    def to_json(self) -> str:
        """ロギング/エコー用の安全なJSON出力"""
        return json.dumps({
            "tool": self.tool,
            "version": self.version,
            "urls": self.urls,
            "headers": self.headers,
            "follow_links": self.follow_links,
            "max_pages": self.max_pages,
            "require_citations": self.require_citations,
            "lang": self.lang,
            "region": self.region,
            "success_message": self.success_message,
            "failure_message": self.failure_message,
        }, ensure_ascii=False)

    @staticmethod
    def json_schema() -> Dict[str, Any]:
        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "$id": "tool.web.read@1",
            "title": "WebReadAction",
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "tool": {"const": "web.read"},
                "version": {"type": "string", "const": "1", "default": "1"},
                "url": {"type": "string", "format": "uri", "pattern": "^(https?)://"},
                "urls": {
                    "type": "array",
                    "items": {"type": "string", "format": "uri", "pattern": "^(https?)://"},
                    "minItems": 1,
                    "uniqueItems": True
                },
                "headers": {
                    "type": "object",
                    "additionalProperties": {"type": "string"}
                },
                "follow_links": {"type": "boolean", "default": False},
                "max_pages": {"type": "integer", "minimum": 1, "maximum": 10, "default": 1},
                "require_citations": {"type": "boolean", "default": True},
                "lang": {"type": "string"},
                "region": {"type": "string"},
                "success_message": {"type": "string"},
                "failure_message": {"type": "string"}
            },
            "required": ["tool"],
            "oneOf": [
                {"required": ["urls"]},
                {"required": ["url"]}
            ],
            "examples": [
                {
                    "tool": "web.read",
                    "urls": ["https://example.com/news/123"],
                    "require_citations": True,
                    "success_message": "記事を読み取りました。",
                    "failure_message": "記事の読み取りに失敗しました：{error}"
                }
            ],
        }

    # ---- 実行メソッド（プラグイン優先 → 不一致なら従来read） ----
    async def execute(self, user_text: str) -> str:
        """
        1) URLに合致する Provider Plugin を優先実行（GitHub等のサービス固有ロジック）
        2) プラグイン不一致なら汎用の read_urls で取得 → LLM向け整形
        """
        # プラグイン用：ReadRequest → read_urls の1件実行をアダプト
        async def _run_webread(reqs: list[ReadRequest]) -> list[ReadResponse]:
            out: list[ReadResponse] = []
            for r in reqs:
                items = await read_urls([r.url], headers=r.headers or {})
                it = items[0] if items else {"url": r.url, "error": "no result"}
                out.append(ReadResponse(
                    url=it.get("url", r.url),
                    status=200 if "error" not in it else 500,
                    headers={},
                    body_text=it.get("raw") or it.get("text") or it.get("summary") or "",
                    body_bytes=None,
                    tag=r.tag,
                ))
            return out

        # --- 1) プラグイン優先 ---
        pr = await try_handle_by_plugin(user_text, self.urls, _run_webread)
        if pr:
            return self._render_plugin_result(pr)

        # --- 2) フォールバック：従来の汎用 read ---
        items = await read_urls(
            self.urls,
            headers=self.headers or {},
            require_citations=self.require_citations,
        )
        return format_read_results_for_llm(items, require_citations=self.require_citations)

    def _render_plugin_result(self, pr: PluginResult) -> str:
        """
        プラグイン非依存の汎用レンダラ:
          1) display_text があればそれを採用
          2) items の中に files(list[{path/url/content?...}]) があれば抜粋＋出典を表示
          3) それ以外は items のダンプ＋ citations を表示
        """
        # 1) プラグインが直接テキストを返している場合
        if getattr(pr, "display_text", None):
            base = str(pr.display_text)
            if pr.citations:
                base += "\n\n出典:\n" + "\n".join(pr.citations)
            return base

        # 2) files を持つitemを探す（type名に依存しない）
        files = []
        for it in pr.items or []:
            cand = it.get("files")
            if isinstance(cand, list) and cand:
                files = cand
                break
        if files:
            parts = []
            for f in files:
                path = f.get("path") or f.get("name") or "(no name)"
                url = f.get("url", "")
                content = (f.get("content") or "")[:1200]
                parts.append(f"### {path}\n```text\n{content}\n```\n出典: {url}" if url else f"### {path}\n```text\n{content}\n```")
            body = "\n\n".join(parts)
            if pr.citations:
                body += "\n\n出典:\n" + "\n".join(pr.citations)
            return body

        # 3) 汎用ダンプ
        body = "取得結果:\n" + "\n".join([str(x) for x in (pr.items or [])])
        if pr.citations:
            body += "\n\n出典:\n" + "\n".join(pr.citations)
        return body
