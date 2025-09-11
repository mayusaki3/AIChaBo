# ai/claude/claude_api.py
import aiohttp, asyncio, json
from typing import List

_ANTHROPIC_BASE = "https://api.anthropic.com/v1"
_ANTHROPIC_VERSION = "2023-06-01"

def _build_messages_from_context(context_list: List[str]) -> tuple[list, str]:
    messages = []
    systems = []
    for msg in context_list or []:
        if not isinstance(msg, str):
            continue
        if msg.startswith("\\s"):
            systems.append(msg.replace("\\s", "", 1).strip()); continue
        if msg.startswith("AIChatBot:"):
            messages.append({"role": "assistant", "content": [{"type": "text", "text": msg.replace("AIChatBot:", "", 1).strip()}]})
        else:
            messages.append({"role": "user", "content": [{"type": "text", "text": msg.strip()}]})
    system_text = "\n".join([s for s in systems if s]).strip()
    return messages, system_text

async def _post(session: aiohttp.ClientSession, url: str, headers: dict, payload: dict, timeout_total: int = 60):
    async with session.post(url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=timeout_total)) as resp:
        text = await resp.text()
        return resp.status, text, resp.headers

async def call_claude_chat(context_list: List[str], api_key: str, model: str = "claude-3-5-sonnet-latest", max_tokens: int = 1024) -> str:
    messages, system_text = _build_messages_from_context(context_list)
    headers = {
        "x-api-key": api_key,
        "anthropic-version": _ANTHROPIC_VERSION,
        "content-type": "application/json"
    }
    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": messages if messages else [{"role": "user", "content": [{"type":"text","text":"Hello"}]}]
    }
    if system_text:
        payload["system"] = system_text

    url = f"{_ANTHROPIC_BASE}/messages"
    try:
        async with aiohttp.ClientSession() as session:
            status, text, headers = await _post(session, url, headers, payload, timeout_total=60)
            if status != 200:
                try:
                    j = json.loads(text); err = j.get("error", {})
                    return f"❌ Claude 応答エラー: status={status}, type={err.get('type')}, message={err.get('message')}"
                except Exception:
                    return f"❌ Claude 応答エラー: status={status}, body={text}"
            j = json.loads(text)
            try:
                content = j.get("content") or []
                texts = [b.get("text") for b in content if isinstance(b, dict) and b.get("type")=="text" and b.get("text")]
                return "\n".join(texts).strip() if texts else "(no content)"
            except Exception:
                return "(no content)"
    except asyncio.TimeoutError:
        return "❌ Claude 応答エラー: Timeout"
    except Exception as e:
        return f"❌ Claude 応答エラー: {e.__class__.__name__}: {str(e) or 'no message'}"

async def generate_claude_image(*args, **kwargs):
    raise RuntimeError("Claude image generation is not supported by Anthropic API (image understanding only).")
