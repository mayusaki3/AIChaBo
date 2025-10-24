# 画像生成（ImageGen）用のサービス層。
# - まずはOpenAIの生成だけ通す。将来モデルを差し替えてもここで局所化。
from ai.openai.openai_api import call_openai_imagegen

async def run_imagegen(prompt: str, api_key: str, model: str):
    """画像生成API呼び出しの薄いラッパ。"""
    return await call_openai_imagegen(prompt, api_key, model)
