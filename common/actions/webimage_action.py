from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
import json

@dataclass
class WebImageAction:
    tool: str
    image_urls: List[str]
    version: str = "1"
    # 解析の指示（任意）
    tasks: Optional[List[str]] = None  # 例: ["count_objects", "extract_text"]
    questions: Optional[List[str]] = None
    prefer_ocr: bool = True
    lang: Optional[str] = None
    # LLM からのテンプレメッセージ（任意）
    success_message: Optional[str] = None
    failure_message: Optional[str] = None

    @staticmethod
    def parse(text: str) -> Optional["WebImageAction"]:
        try:
            obj = json.loads(text)
            t = str(obj.get("tool", "")).replace("_", ".")
            if t != "web.image":
                return None
            src = obj.get("image_urls") or obj.get("images") or obj.get("image") or []
            if isinstance(src, str):
                image_urls = [src]
            elif isinstance(src, list):
                image_urls = [str(u) for u in src if u]
            else:
                image_urls = []
            if not image_urls:
                return None

            return WebImageAction(
                tool="web.image",
                image_urls=image_urls,
                version=str(obj.get("version", "1")),
                tasks=obj.get("tasks"),
                questions=obj.get("questions"),
                prefer_ocr=bool(obj.get("prefer_ocr", True)),
                lang=obj.get("lang"),
                success_message=obj.get("success_message"),
                failure_message=obj.get("failure_message"),
            )
        except Exception:
            return None

    @staticmethod
    def json_schema() -> Dict[str, Any]:
        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "$id": "tool.web.image@1",
            "title": "WebImageAction",
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "tool": {"const": "web.image"},
                "version": {"type": "string", "const": "1", "default": "1"},
                "image_urls": {
                    "type": "array",
                    "items": {"type": "string", "format": "uri"},
                    "minItems": 1
                },
                "tasks": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "（任意）画像に対して行う処理のヒント"
                },
                "questions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "（任意）画像について答えてほしい質問"
                },
                "prefer_ocr": {"type": "boolean", "default": True},
                "lang": {"type": "string"},
                "success_message": {"type": "string"},
                "failure_message": {"type": "string"}
            },
            "required": ["tool", "image_urls"],
            "examples": [
                {
                    "tool": "web.image",
                    "image_urls": ["https://example.com/image.png"],
                    "questions": ["写っている標識の文言は？"],
                    "prefer_ocr": True,
                    "success_message": "画像を解析しました。",
                    "failure_message": "画像解析に失敗しました：{error}"
                }
            ],
        }
