# ui/discord/services/chat_loop.py
# “通常チャット＋JSON応答モード” の本実装。
# - /ac_auth で設定された provider に応じて OpenAI / Claude / Gemini を切替
# - プラグイン system プロンプト（meta.system_prompt）があれば先頭に注入
# - “JSONで返して”のリクエストに対して、多少壊れたJSONでも体裁を整える

from ..utils.log import _print
from common.utils.webread_utils import redact

# 既存の各社ラッパをインポート（あなたのパスに合わせて）
from ai.openai.openai_api import call_chatgpt
from ai.claude.claude_api import call_claude_chat
from ai.gemini.gemini_api import call_gemini_chat

# 将来：プラグイン読み取り結果（PluginResult）から meta.system_prompt を受け取る導線
# いまは prefetch=None だが、webtools→plugins から戻る場合は meta をここに渡す設計

def wants_json(text: str) -> bool:
    """ユーザーがJSONでの応答を希望しているかを簡易判定。"""
    t = (text or "").lower()
    return ("jsonで" in t) or ("respond in json" in t) or ("return json" in t)

def coerce_json(s: str, schema: dict | None = None) -> str:
    """
    モデルの出力に説明やフェンスが混ざっても最低限のJSONに整形する。
    失敗時は {"ok":false,"raw":...} を返す。
    """
    import json, re
    st = (s or "").strip()

    # ```json ... ``` や ``` ... ``` を剥がす
    if st.startswith("```"):
        st = st.strip("` \n")
        if st.lower().startswith("json"):
            st = st[4:].lstrip()

    # 先頭の { ... } または [ ... ] だけを抜き出す最小手当（過剰防衛）
    m = re.search(r"(\{.*\}|\[.*\])", st, flags=re.DOTALL)
    if m:
        st = m.group(1)

    try:
        obj = json.loads(st)
    except Exception:
        return json.dumps({"ok": False, "raw": st[:4000]}, ensure_ascii=False)

    # 簡易スキーマチェック（必須キーのみ）
    if schema:
        missing = [k for k in schema.get("required", []) if k not in obj]
        if missing:
            obj["_missing"] = missing

    return json.dumps(obj, ensure_ascii=False)

async def _call_llm(provider: str, msg_list: list, auth_chat: dict) -> str:
    """プロバイダ分岐の一本化（OpenAI / Claude / Gemini）。"""
    api_key = auth_chat.get("api_key", "")
    model = auth_chat.get("model", "")
    max_tokens = auth_chat.get("max_tokens", 1024)

    try:
        if provider == "OpenAI":
            return await call_chatgpt(msg_list, api_key, model, max_tokens)
        elif provider == "Claude":
            return await call_claude_chat(msg_list, api_key, model, max_tokens)
        elif provider == "Gemini":
            return await call_gemini_chat(msg_list, api_key, model, max_tokens)
        else:
            return "❌ 未対応のプロバイダです。/ac_auth で OpenAI / Claude / Gemini を設定してください。"
    except Exception as e:
        return f"❌ 応答エラー: {redact(str(e))}"

async def run(message, ctx, prefetch):
    """
    message: Discordの受信メッセージ
    ctx: build_context() の戻り（auth/options/system_msgs）
    prefetch: プラグイン実行やURL先読みの結果（将来ここから meta.system_prompt を受け取る）
    """
    user_text = message.content or ""
    provider = ctx["auth"]["chat"].get("provider", "OpenAI")
    auth_chat = ctx["auth"]["chat"]

    # 1) systemメッセージの構築
    system_msgs: list[str] = []
    # (a) 既存の全体/ユーザーsystem（build_contextで積む）
    system_msgs.extend(ctx.get("system_msgs", []))
    # (b) プラグイン system プロンプト（prefetch/meta 経由で受け取る想定）
    #     例：prefetch = {"meta": {"system_prompt": "..."}}
    if prefetch and isinstance(prefetch, dict):
        meta = prefetch.get("meta")
        if isinstance(meta, dict) and meta.get("system_prompt"):
            system_msgs.insert(0, meta["system_prompt"])  # 先頭に挿入

    # 2) メッセージ配列
    msg_list = []
    if system_msgs:
        msg_list.append({"role": "system", "content": "\n".join(system_msgs)})
    msg_list.append({"role": "user", "content": user_text})

    # 3) 呼び出し
    reply = await _call_llm(provider, msg_list, auth_chat)

    # 4) “JSONで返して”の強制整形
    if wants_json(user_text):
        # 必要なら schema={"required": ["summary","sources"]} などを渡す
        reply = coerce_json(reply, schema=None)

    # files は別経路（画像生成/添付）で返す想定。いまは空。
    return reply, []
