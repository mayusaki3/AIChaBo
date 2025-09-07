from __future__ import annotations
import re, json
from typing import Any, Dict, List, Optional

__all__ = [
    "extract_json_object",
    "parse_tool_json",
    "parse_tool_json_multi",  # ← 追加
    "coerce_top_k",
    "coerce_queries",
    "coerce_recency_days",
    "ddg_timelimit",
    "ddg_region_for_lang",
]

_CODEFENCE_RE_START = re.compile(r"^```(?:json|javascript|js|txt)?\s*", re.IGNORECASE)
_CODEFENCE_RE_END = re.compile(r"\s*```$")

def _strip_code_fences(s: str) -> str:
    t = s.strip()
    if t.startswith("```"):
        t = _CODEFENCE_RE_START.sub("", t)
        t = _CODEFENCE_RE_END.sub("", t)
    return t

def _unwrap_extra_braces(t: str) -> str:
    while t.startswith("{{") and t.endswith("}}"):
        t = t[1:-1].strip()
    return t

def extract_json_object(text: str) -> Optional[str]:
    if not isinstance(text, str):
        return None
    t = _strip_code_fences(text)
    t = _unwrap_extra_braces(t.strip())
    if t.startswith("{") and t.endswith("}"):
        try:
            json.loads(t)
            return t
        except Exception:
            pass
    start = t.find("{"); end = t.rfind("}")
    if start != -1 and end != -1 and start < end:
        cand = t[start:end+1].strip()
        try:
            json.loads(cand)
            return cand
        except Exception:
            return None
    return None

def parse_tool_json(text: str, expected_tool: str) -> Optional[Dict[str, Any]]:
    body = extract_json_object(text)
    if not body:
        return None
    try:
        obj = json.loads(body)
    except Exception:
        return None
    if obj.get("tool") != expected_tool:
        return None
    return obj

def parse_tool_json_multi(text: str, expected_tools: List[str]) -> Optional[Dict[str, Any]]:
    """複数のtool名（別名）いずれかに合致したら受理"""
    body = extract_json_object(text)
    if not body:
        return None
    try:
        obj = json.loads(body)
    except Exception:
        return None
    if obj.get("tool") not in expected_tools:
        return None
    return obj

def coerce_top_k(value: Any, default: int = 5, min_k: int = 3, max_k: int = 8) -> int:
    try:
        k = int(value)
    except Exception:
        k = default
    return max(min_k, min(int(k), max_k))

def coerce_queries(obj: Dict[str, Any], max_items: int = 3) -> List[str]:
    out: List[str] = []
    if isinstance(obj.get("queries"), list):
        for q in obj["queries"]:
            if isinstance(q, str) and q.strip():
                out.append(q.strip())
    elif isinstance(obj.get("query"), str) and obj["query"].strip():
        out = [obj["query"].strip()]
    return out[:max_items]

def coerce_recency_days(obj: Dict[str, Any]) -> Optional[int]:
    if obj.get("recency_days") is not None:
        try:
            return int(obj["recency_days"])
        except Exception:
            return None
    tr = obj.get("time_range")
    if isinstance(tr, str) and tr.strip().lower() in ("day","week","month"):
        return 30
    return None

def ddg_timelimit(days: Optional[int]) -> Optional[str]:
    if not days:
        return None
    if days <= 1:
        return "d"
    if days <= 7:
        return "w"
    if days < 365:
        return "m"
    return "y"

_DDG_REGION_BY_LANG = {
    "ja": "jp-jp", "ja-jp": "jp-jp",
    "en": "us-en", "en-us": "us-en",
    "en-gb": "uk-en",
    "de": "de-de", "fr": "fr-fr", "es": "es-es",
    "it": "it-it", "nl": "nl-nl", "ru": "ru-ru",
    "ko": "kr-ko", "zh": "cn-zh",
}
def ddg_region_for_lang(lang: Optional[str]) -> Optional[str]:
    if not lang:
        return None
    key = lang.strip().lower().replace("_","-")
    return _DDG_REGION_BY_LANG.get(key)
