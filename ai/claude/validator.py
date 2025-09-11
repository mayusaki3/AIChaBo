# ai/claude/validator.py
import aiohttp
import json

# 認証情報で指定されたAPIが利用可能かチェックする

_ANTHROPIC_BASE = "https://api.anthropic.com/v1"
_ANTHROPIC_VERSION = "2023-06-01"

async def _post_json(session: aiohttp.ClientSession, url: str, headers: dict, payload: dict):
    async with session.post(url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=12)) as resp:
        return resp.status, await resp.text()

def _headers(api_key: str) -> dict:
    return {
        "x-api-key": api_key,
        "anthropic-version": _ANTHROPIC_VERSION,
        "content-type": "application/json"
    }

# APIキーのチェック
async def is_valid_claude_key(api_key: str):
    url = f"{_ANTHROPIC_BASE}/messages"
    payload = {"model": "claude-3-5-sonnet-latest", "max_tokens": 1, "messages": [{"role": "user", "content": "ping"}]}
    try:
        async with aiohttp.ClientSession() as session:
            status, text = await _post_json(session, url, _headers(api_key), payload)
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
async def is_claude_chat_model_available(api_key: str, model_name: str) -> bool:
    url = f"{_ANTHROPIC_BASE}/messages"
    payload = {"model": model_name, "max_tokens": 1, "messages": [{"role": "user", "content": "ping"}]}
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            status, text = await _post_json(session, url, _headers(api_key), payload)
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
async def is_claude_vision_model_available(api_key: str, model_name: str) -> bool:
    url = f"{_ANTHROPIC_BASE}/messages"
    payload = {
        "model": model_name,
        "max_tokens": 10,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": "Describe this image."},
                {"type": "image", "source": {"type": "url", "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/47/PNG_transparency_demonstration_1.png/320px-PNG_transparency_demonstration_1.png"}}
            ]
        }]
    }
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            status, text = await _post_json(session, url, _headers(api_key), payload)
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
