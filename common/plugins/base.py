# common/plugins/base.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Protocol
import re, urllib.parse as urlparse

@dataclass
class ReadRequest:
    url: str
    method: str = "GET"
    headers: Optional[Dict[str, str]] = None
    body: Optional[bytes] = None
    tag: Optional[str] = None  # レスポンスと結びつけるID

@dataclass
class ReadResponse:
    url: str
    status: int
    headers: Dict[str, str]
    body_text: Optional[str] = None
    body_bytes: Optional[bytes] = None
    tag: Optional[str] = None

@dataclass
class PluginResult:
    items: List[Dict[str, Any]]
    citations: List[str]
    display_text: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None  # 例: {"plugin_name": "github", "system_prompt": "..."}

class ProviderPlugin(Protocol):
    name: str
    domains: List[str]
    def match(self, url: str) -> bool: ...
    def plan(self, url: str, user_text: Optional[str]) -> List[ReadRequest]: ...
    def consume(self, responses: List[ReadResponse]) -> PluginResult: ...
    # 任意：二段目I/Oがある場合
    def has_second_stage(self) -> bool: ...
    def plan_second_stage(self, result: PluginResult) -> List[ReadRequest]: ...
    def consume_second_stage(self, result: PluginResult, responses: List[ReadResponse]) -> PluginResult: ...

def domain_matches(url: str, patterns: List[str]) -> bool:
    try:
        netloc = urlparse.urlparse(url).netloc.lower()
    except Exception:
        return False
    for pat in patterns:
        pat_re = "^" + re.escape(pat).replace("\\*", ".*") + "$"
        if re.fullmatch(pat_re, netloc):
            return True
    return False
