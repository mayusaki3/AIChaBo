# common/actions/imagegen_action.py（抜粋・更新）
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Any, Dict
import json

@dataclass
class ImageGenAction:
    tool: str
    prompt: str
    version: str = "1"
    n: int = 1
    size: Optional[str] = None
    transparent_background: bool = False
    # ★ 追加：LLM からもらうメッセージ（テンプレでもよい）
    success_message: Optional[str] = None
    failure_message: Optional[str] = None

    @staticmethod
    def parse(text: str) -> Optional["ImageGenAction"]:
        try:
            obj = json.loads(text)
            t = obj.get("tool")
            if t not in ("image.generate", "image_generate"):
                return None
            return ImageGenAction(
                tool="image.generate",  # 正規化
                prompt=obj["prompt"],
                version=obj.get("version", "1"),
                n=int(obj.get("n", 1)),
                size=obj.get("size"),
                transparent_background=bool(obj.get("transparent_background", False)),
                success_message=obj.get("success_message"),
                failure_message=obj.get("failure_message"),
            )
        except Exception:
            return None

    @staticmethod
    def json_schema() -> Dict[str, Any]:
        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "$id": "tool.image.generate@1",
            "title": "ImageGenAction",
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "tool": {"const": "image.generate"},
                "version": {"type": "string", "const": "1", "default": "1"},
                "prompt": {"type": "string", "minLength": 1},
                "n": {"type": "integer", "minimum": 1, "maximum": 4, "default": 1},
                "size": {"type": "string", "description": "e.g., '1024x1024'"},
                "transparent_background": {"type": "boolean", "default": False},
                # ★ ここから追加
                "success_message": {
                    "type": "string",
                    "description": "ユーザーに返す成功メッセージ。{n},{size} 等のプレースホルダ可。60文字程度。"
                },
                "failure_message": {
                    "type": "string",
                    "description": "失敗時に返すメッセージ。{error},{n},{size} 等のプレースホルダ可。60文字程度。"
                },
            },
            "required": ["tool", "prompt"],
            "examples": [
                {
                    "tool": "image.generate",
                    "prompt": "A flat, pastel illustration of a sky-blue haired mascot waving hello.",
                    "n": 1,
                    "size": "1024x1024",
                    "transparent_background": False,
                    "success_message": "画像を{n}枚生成しました（{size}）。",
                    "failure_message": "画像生成に失敗しました：{error}"
                }
            ],
        }
