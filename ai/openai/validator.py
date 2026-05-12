import aiohttp
import json
from ai.openai.openai_api import generate_image_from_prompt

# 認証情報で指定されたAPIが利用可能かチェックする

OPENAI_BASE = "https://api.openai.com/v1"
OPENAI_MODELS_ENDPOINT = f"{OPENAI_BASE}/models"
OPENAI_CHAT_ENDPOINT   = f"{OPENAI_BASE}/chat/completions"
OPENAI_VISION_TEST_IMAGE_URL = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)

# 共通HTTPユーティリティ
async def _get_json(session: aiohttp.ClientSession, url: str, headers: dict):
    async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
        return resp.status, await resp.text(), resp.headers

async def _post_json(session: aiohttp.ClientSession, url: str, headers: dict, payload: dict):
    async with session.post(url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=12)) as resp:
        return resp.status, await resp.text(), resp.headers

# APIキーのチェック
async def is_valid_openai_key(api_key: str):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            status, text, _ = await _get_json(session, OPENAI_MODELS_ENDPOINT, headers)
            if status == 200:
                return True
            else:
                err_type, err_msg = None, text
                try:
                    j = json.loads(text)
                    err = j.get("error", {})
                    err_type = err.get("type")
                    err_msg  = err.get("message", text)
                except Exception:
                    pass
                return f"❌ APIキー利用可否確認エラー: status={status}, type={err_type}, message={err_msg}"
    except Exception as e:
        return f"❌ APIキー利用可否確認エラー: {e.__class__.__name__}: {e}"

# チャットモデルのチェック
async def is_openai_chat_model_available(api_key: str, model_name: str) -> bool:
    """指定モデルが chat API で利用可能か検証"""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 1,
    }
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            status, text, _ = await _post_json(session, OPENAI_CHAT_ENDPOINT, headers, payload)
            if status == 200:
                return True
            else:
                err_type, err_msg = None, text
                try:
                    j = json.loads(text)
                    err = j.get("error", {})
                    err_type = err.get("type")
                    err_msg  = err.get("message", text)
                except Exception:
                    pass
                return f"❌ Chatモデル利用可否確認エラー: status={status}, type={err_type}, message={err_msg}"
    except Exception as e:
        return f"❌ Chatモデル利用可否確認エラー: {e.__class__.__name__}: {e}"

# ビジョンモデルのチェック
async def is_openai_vision_model_available(api_key: str, model_name: str) -> bool:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model_name,
        "messages": [
            {"role": "user", "content": [
                {"type": "text", "text": "Describe this image."},
                {"type": "image_url", "image_url": {
                    "url": OPENAI_VISION_TEST_IMAGE_URL
                }}
            ]}
        ],
        "max_tokens": 10,
    }
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            status, text, _ = await _post_json(session, OPENAI_CHAT_ENDPOINT, headers, payload)
            if status == 200:
                return True
            else:
                err_type, err_msg = None, text
                try:
                    j = json.loads(text)
                    err = j.get("error", {})
                    err_type = err.get("type")
                    err_msg  = err.get("message", text)
                except Exception:
                    pass
                return f"❌ Visionモデル利用可否確認エラー: status={status}, type={err_type}, message={err_msg}"
    except Exception as e:
        return f"❌ Visionモデル利用可否確認エラー: {e.__class__.__name__}: {e}"

# イメージ生成モデルのチェック
async def is_openai_imagegen_model_available(api_key: str, model_name: str, image_size: str, image_quality: str) -> bool:
    try:
        await generate_image_from_prompt(
            prompt="A cute baby sea otter",
            api_key=api_key,
            model=model_name,
            size=image_size,
            quality=image_quality,
            timeout_sec=90,
        )
        return True
    except Exception as e:
        return f"❌ ImageGenモデル利用可否確認エラー: {e.__class__.__name__}: {e}"
