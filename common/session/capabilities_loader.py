# common/session/capabilities_loader.py
from __future__ import annotations
import json, re
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from common.utils import jsonc

_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}

def _caps_path(provider: str, model: str) -> Path:
    p = str(provider).strip().lower()
    m = str(model).strip().lower().replace(":", "_").replace("/", "_").replace(" ", "_")
    # 例: ai/openai/capabilities/image_generate_caps_dall_e_3.jsonc
    return Path(f"ai/{p}/capabilities/image_generate_caps_{m}.jsonc")

def load_image_caps(provider: str, model: str) -> Dict[str, Any]:
    path = _caps_path(provider, model)
    if not path.exists():
        return {}
    mtime = path.stat().st_mtime
    cached = _cache.get(str(path))
    if cached and cached[0] == mtime:
        return cached[1]
    try:
        data = jsonc.load_jsonc(path)
    except Exception as e:
        print(f"[capabilities_loader] load_image_caps failed: {path}\n{e}")
        return {}
    # --- エイリアス吸収（旧キー → 新キー） ---
    # allowed_sizes → sizes, allowed_qualities → qualities, n_max → max_n
    aliases_map = {
        "allowed_sizes": "sizes",
        "allowed_qualities": "qualities",
        "n_max": "max_n",
    }
    for old, new in aliases_map.items():
        if old in data and new not in data:
            data[new] = data[old]

    # --- 型の矯正（str → [str]） ---
    for k in ("sizes", "qualities", "aspect_ratios", "long_side_values"):
        if k in data and isinstance(data[k], str):
            data[k] = [data[k]]

    _cache[str(path)] = (mtime, data)
    return data

def normalize_image_params(
    action: Any,
    caps: Dict[str, Any],
    *,
    fallback_sizes: Optional[list[str]] = None,
    fallback_max_n: int = 4,
    fallback_quality: str = "standard",
    passthrough_when_no_caps: bool = True,
) -> tuple[int, str, str, list[str]]:
    """
    戻り値: (n_req, size, quality, warnings)
    """
    warnings: list[str] = []

    # --- caps が無い場合のパススルー（従来挙動を維持したいとき） ---
    if passthrough_when_no_caps and not caps:
        n_req = max(1, int(getattr(action, "n", 1) or 1))
        size  = str(getattr(action, "size", None) or (fallback_sizes[-1] if fallback_sizes else "1024x1024"))
        quality = str(getattr(action, "quality", None) or fallback_quality)
        return n_req, size, quality, []

    # sizes（allowed_sizes も受理）※文字列でも配列化する
    sizes_raw = caps.get("sizes") or caps.get("allowed_sizes") or fallback_sizes or ["1024x1024"]
    if isinstance(sizes_raw, str):
        sizes_raw = [sizes_raw]
    sizes = [str(s).lower().replace("×", "x") for s in sizes_raw]

    # default size
    default_size = str(caps.get("default_size") or (sizes[-1] if sizes else (fallback_sizes[-1] if fallback_sizes else "1024x1024")))
    req_size = getattr(action, "size", None) or default_size
    req_size = str(req_size).lower().replace("×", "x")
    if req_size not in sizes:
        # 近似丸め：一辺の短い方の長さで近いものへ寄せる（同率は並び順優先）
        def _short_side_len(s: str) -> int:
            m = re.match(r"^\s*(\d+)\s*x\s*(\d+)\s*$", s)
            if m:
                return min(int(m.group(1)), int(m.group(2)))
            return 0
        target = min(sizes, key=lambda s: abs(_short_side_len(s) - _short_side_len(req_size)))
        warnings.append(f"size '{req_size}' → '{target}' に正規化")
        req_size = target

    # quality（allowed_qualities も受理、quality_aliases を解釈）
    _raw_q = caps.get("qualities") or caps.get("allowed_qualities") or []
    if isinstance(_raw_q, str):
        _raw_q = [_raw_q]
    allowed_q = [str(q).lower() for q in _raw_q]
    default_q = str(caps.get("default_quality") or fallback_quality).lower()
    req_q = getattr(action, "quality", None)
    req_q = str(req_q or default_q).lower()

    # quality_aliases（例: "hd" → "standard"）
    q_alias = caps.get("quality_aliases") or {}
    if isinstance(q_alias, dict) and req_q in q_alias:
        req_q = str(q_alias[req_q]).lower()

    if allowed_q and req_q not in allowed_q:
        warnings.append(f"quality '{req_q}' は未対応 → '{default_q}' に正規化")
        req_q = default_q
 
    # n
    max_n = int(caps.get("max_n") or fallback_max_n)
    min_n = int(caps.get("min_n") or 1)
    req_n = int(getattr(action, "n", 1) or 1)
    if req_n > max_n:
        warnings.append(f"n={req_n} は上限 {max_n} を超過 → {max_n} に制限")
        req_n = max_n
    if req_n < min_n:
        if min_n > 1:
            warnings.append(f"n={req_n} は下限 {min_n} を下回る → {min_n} に引上げ")
        req_n = min_n

    return req_n, req_size, req_q, warnings
