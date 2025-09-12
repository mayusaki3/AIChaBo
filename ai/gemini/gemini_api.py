# ai/gemini/gemini_api.py
import aiohttp, asyncio, json, base64
from typing import List

_GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"

def _build_contents_from_context(context_list: List[str]) -> tuple[list, str]:
    contents = []
    system_parts = []
    for msg in context_list or []:
        if not isinstance(msg, str):
            continue
        if msg.startswith("\\s"):
            system_parts.append(msg.replace("\\s", "", 1).strip()); continue
        if msg.startswith("AIChatBot:"):
            contents.append({"role": "model", "parts": [{"text": msg.replace("AIChatBot:", "", 1).strip()}]})
        else:
            contents.append({"role": "user", "parts": [{"text": msg.strip()}]})
    system_text = "\n".join([s for s in system_parts if s]).strip()
    return contents, system_text

async def _post(session: aiohttp.ClientSession, url: str, payload: dict, timeout_total: int = 60):
    async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=timeout_total)) as resp:
        text = await resp.text()
        return resp.status, text

def _extract_text_from_generate_content(resp_json: dict) -> str:
    try:
        cand = (resp_json.get("candidates") or [])[0]
        parts = (cand.get("content") or {}).get("parts") or []
        texts = [p.get("text") for p in parts if isinstance(p, dict) and p.get("text")]
        return "\n".join(texts).strip() if texts else ""
    except Exception:
        return ""

def _extract_inline_image_b64_from_generate_content(resp_json: dict) -> str | None:
    """
    Gemini RESTは camelCase（inlineData）で返る。一部実装では snake_case（inline_data）を期待しているため両対応。
    Data URI（uri: "data:image/png;base64,..."}）のパターンも拾う。
    """
    try:
        cand = (resp_json.get("candidates") or [])[0]
        content = cand.get("content") or {}
        parts = content.get("parts") or []
        for p in parts:
            if not isinstance(p, dict):
                continue
            inline = p.get("inline_data") or p.get("inlineData")
            if isinstance(inline, dict):
                # 1) ふつうの base64 フィールド
                data = inline.get("data")
                if isinstance(data, str) and data:
                    return data
                # 2) data URI 形式
                uri = inline.get("uri")
                if isinstance(uri, str) and uri.startswith("data:"):
                    try:
                        return uri.split(",", 1)[1]  # base64 本体
                    except Exception:
                        pass
    except Exception:
        pass
    return None

def _extract_b64_from_imagen_predict(resp_json: dict) -> str | None:
    try:
        preds = resp_json.get("predictions") or []
        if preds:
            p0 = preds[0]
            if isinstance(p0, dict):
                if "bytesBase64Encoded" in p0 and isinstance(p0["bytesBase64Encoded"], str):
                    return p0["bytesBase64Encoded"]
                img = p0.get("image")
                if isinstance(img, dict) and isinstance(img.get("bytesBase64Encoded"), str):
                    return img["bytesBase64Encoded"]
    except Exception:
        pass
    return None

async def call_gemini_chat(context_list: List[str], api_key: str, model: str = "gemini-1.5-pro", max_tokens: int = 1024) -> str:
    contents, system_text = _build_contents_from_context(context_list)
    payload = {
        "contents": contents if contents else [{"role": "user", "parts": [{"text": "Hello"}]}],
        "generationConfig": {"maxOutputTokens": max_tokens}
    }
    if system_text:
        payload["systemInstruction"] = {"role": "system", "parts": [{"text": system_text}]}

    url = f"{_GEMINI_BASE}/models/{model}:generateContent?key={api_key}"
    try:
        async with aiohttp.ClientSession() as session:
            status, text = await _post(session, url, payload, timeout_total=60)
            if status != 200:
                try:
                    j = json.loads(text); err = j.get("error", {})
                    return f"❌ Gemini 応答エラー: status={status}, type={err.get('status')}, message={err.get('message')}"
                except Exception:
                    return f"❌ Gemini 応答エラー: status={status}, body={text}"
            j = json.loads(text)
            out = _extract_text_from_generate_content(j)
            return out or "(no content)"
    except asyncio.TimeoutError:
        return "❌ Gemini 応答エラー: Timeout"
    except Exception as e:
        return f"❌ Gemini 応答エラー: {e.__class__.__name__}: {str(e) or 'no message'}"

async def generate_gemini_image(prompt: str, api_key: str, model: str, size: str, quality: str, timeout_sec: int = 60) -> bytes:
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout_sec)) as session:
            if model.startswith("gemini-"):
                url = f"{_GEMINI_BASE}/models/{model}:generateContent?key={api_key}"
                payload = {
                    "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                }
                status, text = await _post(session, url, payload, timeout_total=timeout_sec)
                if status != 200:
                    try:
                        j = json.loads(text); err = j.get("error", {})
                        raise RuntimeError(f"Gemini image gen failed: status={status}, type={err.get('status')}, message={err.get('message')}")
                    except Exception:
                        raise RuntimeError(f"Gemini image gen failed: status={status}, body={text}")
                j = json.loads(text)
                b64 = _extract_inline_image_b64_from_generate_content(j)
                if not b64:
                    raise RuntimeError(f"Gemini image gen: no inline_data in response: {j}")
                return base64.b64decode(b64)

            elif model.startswith("imagen-"):
                url = f"{_GEMINI_BASE}/models/{model}:predict?key={api_key}"
                params = {"sampleCount": 1}
                if size and isinstance(size, str):
                    try:
                        w = int(size.split("x")[0].strip())
                        params["sampleImageSize"] = "2K" if w >= 1536 else "1K"
                    except Exception:
                        pass
                payload = {
                    "instances": [{"prompt": prompt}],
                    "parameters": params,
                }
                status, text = await _post(session, url, payload, timeout_total=timeout_sec)
                if status != 200:
                    try:
                        j = json.loads(text); err = j.get("error", {})
                        raise RuntimeError(f"Imagen predict failed: status={status}, type={err.get('status')}, message={err.get('message')}")
                    except Exception:
                        raise RuntimeError(f"Imagen predict failed: status={status}, body={text}")
                j = json.loads(text)
                b64 = _extract_b64_from_imagen_predict(j)
                if not b64:
                    raise RuntimeError(f"Imagen predict: no base64 payload in response: {j}")
                return base64.b64decode(b64)

            else:
                raise RuntimeError(f"Unknown Gemini image model family: {model} (expected gemini-*/imagen-*)")
    except Exception as e:
        raise
