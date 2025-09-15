# common/utils/attachments.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, List, Tuple
import mimetypes

@dataclass
class Attachment:
    url: str
    filename: Optional[str] = None
    content_type: Optional[str] = None
    is_image: bool = False

def build_attachment(url: str, filename: Optional[str] = None, content_type: Optional[str] = None) -> Attachment:
    ct = content_type or (mimetypes.guess_type(filename, strict=False)[0] if filename else None)
    is_img = (ct or "").startswith("image/")
    return Attachment(url=url, filename=filename, content_type=ct, is_image=is_img)

def split_attachments(items: List[Attachment]) -> Tuple[List[Attachment], List[Attachment]]:
    imgs = [a for a in items if a.is_image]
    docs = [a for a in items if not a.is_image]
    return imgs, docs

def render_append_block(
    imgs: List[Attachment],
    docs: List[Attachment],
    *,
    image_header: str = "[添付画像]",
    file_header: str = "[添付ファイル]",
) -> str:
    parts: List[str] = []
    if imgs:
        parts.append(image_header + "\n" + "\n".join(f"- {a.url}" for a in imgs))
    if docs:
        parts.append(file_header + "\n" + "\n".join(f"- {a.filename or 'file'}: {a.url}" for a in docs))
    return ("\n\n" + "\n".join(parts)) if parts else ""
