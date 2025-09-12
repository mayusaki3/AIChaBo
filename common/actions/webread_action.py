from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
import json

@dataclass
class WebReadAction:
    tool: str
    urls: List[str]
    version: str = "1"
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
            if not urls:
                return None

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
            )
        except Exception:
            return None

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
                "urls": {
                    "type": "array",
                    "items": {"type": "string", "format": "uri"},
                    "minItems": 1
                },
                "follow_links": {"type": "boolean", "default": False},
                "max_pages": {"type": "integer", "minimum": 1, "maximum": 10, "default": 1},
                "require_citations": {"type": "boolean", "default": True},
                "lang": {"type": "string"},
                "region": {"type": "string"},
                "success_message": {"type": "string"},
                "failure_message": {"type": "string"}
            },
            "required": ["tool", "urls"],
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
