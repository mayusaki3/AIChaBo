# common/session/prompt_loader.py
from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
import json
import re

# 既存セッションマネージャを参照
from common.session.user_session_manager import user_session_manager
from common.session.server_session_manager import server_session_manager

from common.actions.websearch_action import WebSearchAction
from common.actions.webread_action import WebReadAction
from common.actions.imagegen_action import ImageGenAction
from common.actions.webimage_action import WebImageAction

try:
    from zoneinfo import ZoneInfo  # py>=3.9
except Exception:
    ZoneInfo = None

# ===== 例外 =====
class AuthNotConfigured(Exception):
    """認証情報が未登録"""
    pass

# ===== 既知ツール（存在する *.txt だけ読む） =====
_TOOL_FILES = [
    "image_generate.txt",
    "web_search.txt",
    "web_read.txt",
    "web_image.txt",
]

# ===== キャッシュ =====
# 本文キャッシュ: key=(role, provider) -> {"text":str, "mtimes":dict[str,float]}
_CACHE: Dict[Tuple[str, str], Dict[str, object]] = {}
# 最終ロード概要: role -> {"provider":str,"loaded_at":str,"length":int}
_LAST: Dict[str, Dict[str, object]] = {
    "chat":   {"provider": "default", "loaded_at": None, "length": 0},
    "vision": {"provider": "default", "loaded_at": None, "length": 0},
    "image":  {"provider": "default", "loaded_at": None, "length": 0},
}
# スニペット（reply_to.txt / summary.txt など）用のキャッシュ
# キーは実ファイルパス（resolve後の文字列）。値は {"text": str, "mtime": float}
_SNIPPET_CACHE: Dict[str, Dict[str, object]] = {}

# ===== util =====
def _strip_comments_keep_code(text: str) -> str:
    """
    行頭 '#'(空白許容) をコメントとして削除。ただし ``` フェンス内はそのまま。
    """
    if not text:
        return text
    out_lines = []
    in_fence = False
    fence_pat = re.compile(r"^\s*```")
    for line in text.splitlines():
        if fence_pat.match(line):
            in_fence = not in_fence
            out_lines.append(line)
            continue
        if not in_fence and re.match(r"^\s*#(?!#)", line):
            # 単純なコメント行は捨てる（'##' 等を残したければ条件調整）
            continue
        out_lines.append(line)
    return "\n".join(out_lines).strip()

def _extract_provider(auth_data: dict, section_keys: list[str]) -> Optional[str]:
    """
    auth_data から候補セクション（例: ["chat"], ["vision","chat"], ["image","imagegen",...]）を順に探し、
    見つかった最初の dict の provider を返す。未設定なら None。
    """
    for k in section_keys:
        sec = auth_data.get(k)
        if isinstance(sec, dict):
            p = sec.get("provider")
            if p:
                return _normalize_provider(p)
    return None

def _now_jst_str() -> str:
    """
    JST 現在時刻を 'YYYY-MM-DD HH:MM' で返す。
    tzdata が入っていない環境（Windows等）では UTC+9 にフォールバック。
    """
    if ZoneInfo is not None:
        try:
            tz = ZoneInfo("Asia/Tokyo")
            return datetime.now(tz).strftime("%Y-%m-%d %H:%M")
        except Exception:
            # tzdata 未インストール or 無効など
            pass
    # フォールバック（UTC+9）
    return (datetime.now(timezone.utc) + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M")

def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except Exception:
        return ""

def _first(paths: List[Path]) -> Optional[Path]:
    for p in paths:
        if p.exists():
            return p
    return None

def _prompt_dir(provider: str) -> Path:
    return Path("ai")/provider/"system_prompts"

def _pick_file(provider: str, name: str) -> Optional[Path]:
    """ai/{provider}/system_prompts/name → なければ ai/default/system_prompts/name"""
    base = _prompt_dir(provider)
    fallback = _prompt_dir("default")
    return _first([base/name, fallback/name])

def _collect_paths(provider: str) -> Dict[str, object]:
    """provider 用の各テキストとツールテキストの Path を収集"""
    out: Dict[str, object] = {
        "general":   _pick_file(provider, "general.txt"),
        "aichabo":   _pick_file(provider, "aichabo.txt"),
        "injection": _pick_file(provider, "injection.txt"),
        "tools":     [],
    }
    tool_paths: List[Path] = []
    for fname in _TOOL_FILES:
        p = _pick_file(provider, fname)
        if p:
            tool_paths.append(p)
    out["tools"] = tool_paths
    return out

def _schema_for_tool_fname(fname: str) -> Optional[str]:
    mapping = {
        "web_search.txt": WebSearchAction,
        "web_read.txt": WebReadAction,
        "image_generate.txt": ImageGenAction,
        "web_image.txt": WebImageAction,
    }
    cls = mapping.get(fname)
    if not cls or not hasattr(cls, "json_schema"):
        return None
    try:
        return json.dumps(cls.json_schema(), ensure_ascii=False, indent=2)  # type: ignore
    except Exception:
        return None

def _normalize_provider(name: Optional[str]) -> str:
    """認証に入っている provider 名をディレクトリ名へ正規化"""
    if not name:
        return "default"
    n = str(name).strip().lower()
    # 想定されるエイリアス
    if n in ("openai", "gpt", "oai"):
        return "openai"
    if n in ("google", "gemini", "g"):
        return "google"
    if n in ("anthropic", "claude", "a"):
        return "claude"
    if n in ("default",):
        return "default"
    # 未知はそのままディレクトリ名として解釈（存在しなければ default にフォールバックが効く）
    return n

def _resolve_auth_providers(user_id: int, guild_id: int) -> Dict[str, str]:
    """
    認証の取得優先度:
      1) ユーザーセッションがあれば user を使う
      2) なければサーバーセッションを使う
      3) どちらも無ければ未登録
    """
    auth_data = None

    # ✅ まず user_session を見る
    if user_session_manager.has_session(user_id):
        auth_data = user_session_manager.get_session(user_id)
    # 次に server_session
    elif server_session_manager.has_session(guild_id):
        auth_data = server_session_manager.get_session(guild_id)

    if not auth_data:
        raise AuthNotConfigured("⚠️ あいちゃぼと会話するには /ac_auth で認証情報を登録してください。")

    # 各ロールごとのプロバイダを抽出
    # chat は chat セクション固定
    chat_provider = _extract_provider(auth_data, ["chat"]) or "default"

    # vision は「vision が無ければ chat の provider を流用」
    vision_provider = _extract_provider(auth_data, ["vision"]) or chat_provider

    # image は実装差異に備えて複数キーを許容（image / imagegen / image_generate / image.generate / img / images）
    image_provider = _extract_provider(
        auth_data,
        ["image", "imagegen", "image_generate", "image.generate", "img", "images"]
    ) or chat_provider

    return {
        "chat": chat_provider,
        "vision": vision_provider,
        "image": image_provider,
    }

def _build_parts(role: str, provider: str) -> Tuple[dict, Dict[str, float]]:
    """
    置換前のパーツを返す:
      parts = {"head": str, "inj": str, "tail": str}
      mtimes = {path: mtime, ...}
    """
    paths = _collect_paths(provider)

    sections = []  # for head
    for key in ("general", "aichabo"):
        p = paths.get(key)
        if isinstance(p, Path):
            sections.append(_strip_comments_keep_code(_read_text(p)))
    head = "\n\n".join([s for s in sections if s and s.strip()])

    inj_p = paths.get("injection")
    inj_raw = _read_text(inj_p) if isinstance(inj_p, Path) else ""
    inj = _strip_comments_keep_code(inj_raw)  # 置換は get_prompt_for_ctx で行う

    tails = []
    if role == "chat":
        for tp in (paths.get("tools") or []):
            body = _strip_comments_keep_code(_read_text(tp))
            if body:
                tails.append(body)
            schema_json = _schema_for_tool_fname(tp.name)
            if schema_json:
                tails.append(f"```json\n{schema_json}\n```")
    tail = "\n\n".join([t for t in tails if t and t.strip()])

    return {"head": head, "inj": inj, "tail": tail}

# ===== 公開 API =====
def load_for_ctx(user_id: int, guild_id: int, *, force: bool = False) -> None:
    providers = _resolve_auth_providers(user_id, guild_id)
    now_iso = datetime.utcnow().isoformat(timespec="seconds") + "Z"

    for role in ("chat", "vision", "image"):
        provider = providers[role]
        key = (role, provider)
        if not force and key in _CACHE:
            continue

        parts = _build_parts(role, provider)
        _CACHE[key] = {"head": parts["head"], "inj": parts["inj"], "tail": parts["tail"]}
        # _LAST の length は get 時点の組み立て後の長さで更新します
        _LAST[role] = {"provider": provider, "loaded_at": now_iso, "length": len(parts["head"]) + len(parts["inj"]) + len(parts["tail"])}

    if force:
        # スニペットキャッシュも同時にクリア
        _SNIPPET_CACHE.clear()

def is_loaded_for_ctx(role: str, user_id: int, guild_id: int) -> bool:
    try:
        providers = _resolve_auth_providers(user_id, guild_id)
    except AuthNotConfigured:
        return False
    provider = providers.get(role, "default")
    return (role, provider) in _CACHE

def get_prompt_for_ctx(role: str, user_id: int, guild_id: int,
                       extra_vars: Optional[Dict[str, str]] = None) -> str:
    providers = _resolve_auth_providers(user_id, guild_id)
    provider = providers[role]
    key = (role, provider)
    if key not in _CACHE:
        raise RuntimeError("prompt_loader: not loaded yet. Call load_for_ctx(...).")

    head = _CACHE[key].get("head") or ""  # 読込時に strip 済み

    # 置換マップを合成（now_jst は常に供給、extra_vars で上書きしない）
    vars_map = {"now_jst": _now_jst_str()}
    if extra_vars:
        # None/空は無視、文字列化しておく
        for k, v in extra_vars.items():
            if v is not None:
                vars_map[k] = str(v)
    # まとめて置換
    inj = _CACHE[key].get("inj") or ""
    for k, v in vars_map.items():
        inj = inj.replace("{"+k+"}", v)

    tail = _CACHE[key].get("tail") or ""  # 読込時に strip 済み
    text = "\n\n".join([t for t in (head, inj, tail) if t and str(t).strip()])

    # 長さをここで更新（任意）
    _LAST[role]["length"] = len(text)

    return text

# --- 任意スニペットの読み出しAPI（返信時などに使う） ---
def read_snippet_for_ctx(name: str, user_id: int, guild_id: int) -> str:
    """
    ai/{provider}/system_prompts/{name} を読み、無ければ ai/default/... を読む。
    スニペット（reply_to / summary など）をキャッシュ付きで返す。
    認証未設定なら空文字を返す。
    - 取得時に # 行コメントは除去（コードフェンス内は温存）
    """
    try:
        providers = _resolve_auth_providers(user_id, guild_id)
        provider = providers.get("chat", "default")
    except AuthNotConfigured:
        return ""
    p = _pick_file(provider, name + ".txt")
    if not p:
        return ""

    key = str(p.resolve()).lower()
    entry = _SNIPPET_CACHE.get(key)
    if entry is not None:
        return str(entry["text"])

    # 初回だけ読み込む（#行はここで除去）。以降は -loadprompt(force=True) まで固定。
    text = _strip_comments_keep_code(_read_text(p))
    _SNIPPET_CACHE[key] = {"text": text}
    return text

def export_for_ctx(role: str, user_id: int, guild_id: int, extra_vars: dict | None = None) -> bytes:
    """
    -expprompt 用。chat/vision/image いずれも、get_prompt_for_ctx の出力をそのまま返す。
    extra_vars に {"thread_name": "..."} などを渡すと、injection 内で置換される。
    """
    try:
        main = get_prompt_for_ctx(role, user_id, guild_id, extra_vars=extra_vars)
        return main.encode("utf-8")
    except AuthNotConfigured:
        return b""
    except Exception:
        return b""

def dump_state_for_ctx(user_id: int, guild_id: int) -> Dict[str, Dict[str, object]]:
    """
    /ac_status 表示用
    """
    try:
        providers = _resolve_auth_providers(user_id, guild_id)
    except AuthNotConfigured:
        providers = {"chat":"(not set)","vision":"(not set)","image":"(not set)"}
    out: Dict[str, Dict[str, object]] = {}
    for role in ("chat","vision","image"):
        out[role] = {
            "provider": providers.get(role, "(not set)"),
            "loaded_at": _LAST[role]["loaded_at"],
            "length": _LAST[role]["length"],
        }
    return out
