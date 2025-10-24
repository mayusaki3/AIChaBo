# 画像認識（Vision）用のサービス層。
# - まずはOpenAI Visionだけ通す（Claude/Geminiは後で追加）
from ai.openai.openai_api import call_openai_vision

async def run_vision(messages, api_key, model, max_tokens=1024):
    """Vision APIを叩いて結果文字列を返す簡易ラッパ。"""
    return await call_openai_vision(messages, api_key, model, max_tokens)
