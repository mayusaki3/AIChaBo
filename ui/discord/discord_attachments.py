# ui/discord/discord_attachments.py
from __future__ import annotations
from typing import Iterable, List
from common.utils.attachments import Attachment, build_attachment

def from_discord_attachments(atts: Iterable) -> List[Attachment]:
    out: List[Attachment] = []
    for a in atts or []:
        try:
            url = getattr(a, "url", None)
            filename = getattr(a, "filename", None)
            content_type = getattr(a, "content_type", None)
            if not url:
                continue
            out.append(build_attachment(url, filename, content_type))
        except Exception:
            continue
    return out
