from __future__ import annotations
from dataclasses import dataclass
from typing import ClassVar, List, Optional
from .action_utils import parse_tool_json, coerce_queries, coerce_top_k, coerce_recency_days

@dataclass
class WebSearchAction:
    tool: ClassVar[str] = "web.search"

    queries: List[str]
    top_result: int
    recency_days: Optional[int]
    require_citations: bool
    lang: Optional[str] = None
    region: Optional[str] = None

    @classmethod
    def parse(cls, text: str) -> Optional["WebSearchAction"]:
        obj = parse_tool_json(text, expected_tool=cls.tool)
        if not obj:
            return None
        queries = coerce_queries(obj)
        if not queries:
            return None
        top_result = coerce_top_k(obj.get("top_result", obj.get("top_k", 5)))
        recency_days = coerce_recency_days(obj)
        require_citations = bool(obj.get("require_citations", True))
        lang = (obj.get("lang") or None)
        region = (obj.get("region") or None)
        return cls(queries=queries, top_result=top_result, recency_days=recency_days,
                   require_citations=require_citations, lang=lang, region=region)

    @classmethod
    def json_schema(cls) -> dict:
        return {
            "$id": "tool.web.search",
            "title": "WebSearchAction",
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "tool": {"const": "web.search"},
                "queries": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 3},
                "top_result": {"type": "integer", "minimum": 1, "maximum": 8, "default": 5},
                "recency_days": {"type": "integer", "minimum": 1},
                "require_citations": {"type": "boolean", "default": True},
                "lang": {"type": "string"},
                "region": {"type": "string"}
            },
            "required": ["tool", "queries"]
        }
