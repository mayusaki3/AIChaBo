# -*- coding: utf-8 -*-
"""
機密文字列をログ出力前にマスクする簡易関数
"""
import re
from typing import Any

_PATTERNS = [
    re.compile(r'(api[_-]?key\s*[:=]\s*)([A-Za-z0-9_\-]{8,})', re.IGNORECASE),
    re.compile(r'(sk-[A-Za-z0-9]{8,})'),               # OpenAI等
    re.compile(r'(ghp_[A-Za-z0-9]{20,})'),             # GitHub
    re.compile(r'(AIza[0-9A-Za-z_\-]{20,})'),          # Google
]

def redact(obj: Any, keep: int = 4) -> str:
    """文字列中の“それっぽい鍵”を *** でマスク"""
    s = str(obj)
    for pat in _PATTERNS:
        def _mask(m):
            g = m.group(0)
            if m.lastindex and m.lastindex >= 2:
                # “prefix + 値” 形式（group1=prefix, group2=value）
                return f"{m.group(1)}***"
            # 値だけの一致
            head = g[:keep]
            return f"{head}***"
        s = pat.sub(_mask, s)
    return s
