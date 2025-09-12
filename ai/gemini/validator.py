# ai/gemini/validator.py
import aiohttp
import json

# 認証情報で指定されたAPIが利用可能かチェックする

_GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"
_VISION_TEST_IMAGE_URL = "https://upload.wikimedia.org/wikipedia/commons/3/3f/JPEG_example_flower.jpg"

# 共通HTTPユーティリティ ----
async def _get_json(session: aiohttp.ClientSession, url: str):
    async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
        return resp.status, await resp.text()

async def _post_json(session: aiohttp.ClientSession, url: str, payload: dict):
    async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as resp:
        return resp.status, await resp.text()

async def _get_model(session: aiohttp.ClientSession, api_key: str, model: str):
    url = f"{_GEMINI_BASE}/models/{model}?key={api_key}"
    async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
        return resp.status, await resp.text()

async def _post_generate_content(session, api_key, model, prompt_text: str):
    url = f"{_GEMINI_BASE}/models/{model}:generateContent?key={api_key}"
    payload = {"contents": [{"parts": [{"text": prompt_text}]}]}
    return await _post_json(session, url, payload)

async def _post_predict_imagen(session, api_key, model, prompt_text: str):
    # Imagen は predict を使う（sampleCount=1 の最小）
    url = f"{_GEMINI_BASE}/models/{model}:predict?key={api_key}"
    payload = {"instances": [{"prompt": prompt_text}], "parameters": {"sampleCount": 1}}
    return await _post_json(session, url, payload)

# APIキーのチェック
async def is_valid_gemini_key(api_key: str):
    url = f"{_GEMINI_BASE}/models?key={api_key}"
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            status, text = await _get_json(session, url)
            if status == 200:
                return True
            else:
                err_type, err_msg = None, text
                try:
                    j = json.loads(text)
                    err = j.get("error", {})
                    err_type = err.get("status")
                    err_msg  = err.get("message", text)
                except Exception:
                    pass
                return f"❌ APIキー利用可否確認エラー: status={status}, type={err_type}, message={err_msg}"
    except Exception as e:
        return f"❌ APIキー利用可否確認エラー: {e.__class__.__name__}: {e}"

async def _gen_content(session: aiohttp.ClientSession, api_key: str, model: str, payload: dict):
    url = f"{_GEMINI_BASE}/models/{model}:generateContent?key={api_key}"
    return await _post_json(session, url, payload)

# チャットモデルのチェック
async def is_gemini_chat_model_available(api_key: str, model_name: str) -> bool:
    payload = {"contents": [{"role": "user", "parts": [{"text": "ping"}]}]}
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            status, text = await _gen_content(session, api_key, model_name, payload)
            if status == 200:
                return True
            else:
                err_type, err_msg = None, text
                try:
                    j = json.loads(text)
                    err = j.get("error", {})
                    err_type = err.get("status")
                    err_msg  = err.get("message", text)
                except Exception:
                    pass
                return f"❌ Chatモデル利用可否確認エラー: status={status}, type={err_type}, message={err_msg}"
    except Exception as e:
        return f"❌ Chatモデル利用可否確認エラー: {e.__class__.__name__}: {e}"

# ビジョンモデルのチェック
async def is_gemini_vision_model_available(api_key: str, model_name: str) -> bool:
    payload = {
        "contents": [{
            "role": "user",
            "parts": [{
                "text": f"Describe the image at this URL in one short sentence: {_VISION_TEST_IMAGE_URL}"
            }]
        }],
        "tools": [{"url_context": {}}]
    }
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            status, text = await _gen_content(session, api_key, model_name, payload)
            if status == 200:
                return True
            else:
                err_type, err_msg = None, text
                try:
                    j = json.loads(text)
                    err = j.get("error", {})
                    err_type = err.get("status")
                    err_msg  = err.get("message", text)
                except Exception:
                    pass
                return f"❌ Visionモデル利用可否確認エラー: status={status}, type={err_type}, message={err_msg}"
    except Exception as e:
        return f"❌ Visionモデル利用可否確認エラー: {e.__class__.__name__}: {e}"

# イメージ生成モデルのチェック
async def is_gemini_imagegen_model_available(api_key: str, model_name: str):
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            # 1) モデルの存在/権限チェック
            status1, text1 = await _get_model(session, api_key, model_name)
            if status1 != 200:
                try:
                    j = json.loads(text1); err = j.get("error", {})
                    return f"❌ ImageGenモデル照会エラー: status={status1}, type={err.get('status')}, message={err.get('message')}"
                except Exception:
                    return f"❌ ImageGenモデル照会エラー: status={status1}, body={text1}"

            # 2) 画像生成の簡易テスト（1枚）
            prompt = "A minimal red circle centered on a plain white background."
            if model_name.startswith("gemini-"):
                status2, text2 = await _post_generate_content(session, api_key, model_name, prompt)
            elif model_name.startswith("imagen-"):
                status2, text2 = await _post_predict_imagen(session, api_key, model_name, prompt)
            else:
                return f"❌ ImageGen未対応モデル系列エラー: model={model_name}"
            if status2 == 200:
                return True
            else:
                try:
                    j2 = json.loads(text2); err2 = j2.get("error", {})
                    return f"❌ ImageGen生成テストエラー: status={status2}, type={err2.get('status')}, message={err2.get('message')}"
                except Exception:
                    return f"❌ ImageGen生成テストエラー: status={status2}, body={text2}"
    except Exception as e:
        return f"❌ ImageGenモデル利用可否確認エラー: {e.__class__.__name__}: {e}"
