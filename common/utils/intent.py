# intent.py — インテントYAMLローダ & 汎用ルール実行ユーティリティ
#
# 使い方（ランタイム）:
#   from common.utils.intent import (
#       build_tool_hint_auto,           # 自動判定でヒント文字列を得る
#       build_tool_hint_from_config,    # インテント名を明示してヒント文字列を得る
#       detect_intent,                  # 文章からインテント名を推定
#       build_fallback_queries,         # ゼロ件時の再検索クエリをYAMLに従って構築
#       get_search_defaults,            # 検索の推奨パラメータ（recency_days など）を取得
#       clear_intent_caches,            # YAMLの再読込（/ac_status -loadintent から呼ぶ）
#   )
#
# YAML配置:
#   common/config/intents/<intent>.<locale>.yaml
#   例) weather.ja.yaml
#   common/config/dictionaries/*.yaml  （aliases で参照）
#
# ヒントの注入例:
#   hint = build_tool_hint_auto("明日の大阪の天気は？", locale="ja")
#   if hint:
#       context_list.append("\\s " + hint)
#
# CLIテスト:
#   python -m common.utils.intent_test "明日の大阪の天気は？"
#
# 依存:
#   - PyYAML>=6.0.1（requirements.txt に追記済みであること）
#   - Python 3.10+

from __future__ import annotations

from pathlib import Path
from functools import lru_cache
from typing import Any, Dict, List, Tuple, Optional
import yaml
import re
from datetime import datetime, timedelta, timezone

# ---- 環境定数 ----
JST = timezone(timedelta(hours=9))
CONFIG_DIR = Path("common/config")


# =========================
# YAML ロード & キャッシュ
# =========================

@lru_cache(maxsize=32)
def load_intent_config(name: str, locale: str = "ja") -> dict:
    """intent の YAML を読み込む（存在しなければ {}）"""
    p = CONFIG_DIR / "intents" / f"{name}.{locale}.yaml"
    try:
        with p.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}


@lru_cache(maxsize=32)
def load_dict(path: str) -> dict:
    """辞書 YAML を読み込む（存在しなければ {}）"""
    p = Path(path)
    try:
        with p.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}


@lru_cache(maxsize=8)
def list_intent_names(locale: str = "ja") -> tuple[str, ...]:
    """利用可能な intent 名を列挙（<name>.<locale>.yaml を探索）"""
    root = CONFIG_DIR / "intents"
    names: list[str] = []
    if root.exists():
        for y in root.glob(f"*.{locale}.yaml"):
            n = y.name[:-(len(f".{locale}.yaml"))]  # "weather.ja.yaml" -> "weather"
            if n:
                names.append(n)
    return tuple(sorted(set(names)))


def clear_intent_caches() -> None:
    """lru_cache をクリアして YAML を再読込可能にする。/ac_status -loadintent から呼ぶ"""
    try:
        load_intent_config.cache_clear()
        load_dict.cache_clear()
        list_intent_names.cache_clear()
    except Exception:
        pass


# ==============
# 内部ユーティリティ
# ==============

def _fmt_date_jp(dt: datetime) -> str:
    return f"{dt.year}年{dt.month}月{dt.day}日"


def _apply_alias(value: Optional[str], alias_path: Optional[str]) -> Optional[str]:
    if not value or not alias_path:
        return value
    table = load_dict(alias_path)
    return table.get(value, value)


def _apply_text_normalizers(text: str, steps: List[Dict[str, Any]]) -> str:
    """
    text_normalizers を順に適用。
    - strip_tokens: 指定トークンを除去
    - strip_particle: 語尾の助詞を除去（例: "の"）
    - regex_replace: 正規表現置換
    """
    t = text or ""
    for st in steps or []:
        op = st.get("op")
        if op == "strip_tokens":
            for tok in st.get("tokens", []) or []:
                t = t.replace(tok, "")
        elif op == "strip_particle":
            p = st.get("particle", "")
            if p:
                t = re.sub(rf"{re.escape(p)}+$", "", t)
        elif op == "regex_replace":
            pat = st.get("pattern", "")
            rep = st.get("replace", "")
            if pat:
                t = re.sub(pat, rep, t)
    return t.strip()


def _resolve_dates(text: str, date_rules: List[Dict[str, Any]] | None) -> List[datetime]:
    """
    date_rules に従い相対表現を具体日付に展開。
    - offset_days: 現在(日本時間)の0時起点で日数オフセット
    - weekend: 今週末/来週末など（week_offset=0/1）で土日2件を返す
    未該当なら []。
    """
    if not date_rules:
        return []
    now = datetime.now(JST).replace(hour=0, minute=0, second=0, microsecond=0)
    out: List[datetime] = []
    for rule in date_rules:
        m = rule.get("match")
        op = rule.get("op")
        if not (m and op):
            continue
        if m not in text:
            continue
        if op == "offset_days":
            val = int(rule.get("value", 0))
            out.append(now + timedelta(days=val))
        elif op == "weekend":
            week_offset = int(rule.get("week_offset", 0))
            dow = now.weekday()  # Mon=0..Sun=6
            days_until_sat = ((5 - dow) % 7) + 7 * week_offset
            sat = now + timedelta(days=days_until_sat)
            sun = sat + timedelta(days=1)
            out.extend([sat, sun])
    # 重複削除・昇順
    uniq: List[datetime] = []
    seen = set()
    for d in out:
        key = d.toordinal()
        if key not in seen:
            seen.add(key)
            uniq.append(d)
    return uniq


def _extract_fields(text: str,
                    extractors: List[Dict[str, Any]],
                    aliases: Dict[str, Any]) -> Dict[str, str]:
    """
    抽出定義を実行:
    - type=regex: pattern の第1キャプチャを name に格納
    - post: [{op: apply_alias, dict: "path/to/dict.yaml"}] を順に適用
    """
    out: Dict[str, str] = {}
    for ex in extractors or []:
        name = ex.get("name")
        tp = ex.get("type")
        if tp == "regex" and name and ex.get("pattern"):
            m = re.search(ex["pattern"], text)
            if m:
                val = m.group(1)
                for post in ex.get("post", []) or []:
                    if post.get("op") == "apply_alias":
                        val = _apply_alias(val, post.get("dict")) or val
                out[name] = val
    return out


# ==========
# 公開API
# ==========

def detect_intent(user_text: str, locale: str = "ja") -> Optional[str]:
    """triggers.any_keywords にヒットした最初の intent 名を返す。"""
    for name in list_intent_names(locale):
        cfg = load_intent_config(name, locale)
        kws = (cfg.get("triggers", {}) or {}).get("any_keywords", []) or []
        if any(k in (user_text or "") for k in kws):
            return name
    return None


def get_search_defaults(intent_name: str, locale: str = "ja") -> Dict[str, Any]:
    """search_defaults ブロック（recency_days / region / top_result 等）を返す。"""
    cfg = load_intent_config(intent_name, locale)
    return cfg.get("search_defaults", {}) or {}


def build_fallback_queries(intent_name: str,
                           queries: List[str],
                           locale: str = "ja") -> Tuple[List[str], Optional[int]]:
    """
    fallback.steps を適用して再検索クエリを構築。戻り値は (queries, recency_days_override)。
      - strip_date_string: "2025年9月20日" を除去
      - replace: pairs: [["A", "B"], ...] 文字列置換
      - strip_site_filter: " site:example.com" を除去
    """
    cfg = load_intent_config(intent_name, locale)
    fb = cfg.get("fallback", {}) or {}
    steps = fb.get("steps", []) or []
    qlist = list(queries or [])
    out: List[str] = []

    def _strip_date_string(q: str) -> str:
        return re.sub(r"\s*\d{4}年\d{1,2}月\d{1,2}日", "", q)

    def _strip_site(q: str) -> str:
        return re.sub(r"\s*site:[^\s]+", "", q)

    for q in qlist:
        cand = [q]
        for st in steps:
            op = st.get("op")
            if op == "strip_date_string":
                cand = [_strip_date_string(x) for x in cand]
            elif op == "replace":
                for a, b in st.get("pairs", []) or []:
                    cand = [x.replace(a, b) for x in cand]
            elif op == "strip_site_filter":
                cand = [_strip_site(x) for x in cand]
        out.extend(cand)

    # 重複・空除去、上限
    seen, dedup = set(), []
    for s in out:
        s = (s or "").strip()
        if s and s not in seen:
            seen.add(s)
            dedup.append(s)

    limit = int(fb.get("limit", 3))
    return (dedup[:limit] or ["天気 週間"], fb.get("recency_days", None))


def build_tool_hint_from_config(intent_name: str,
                                user_text: str,
                                locale: str = "ja") -> Optional[str]:
    """
    YAMLに基づき、ヒント文（queries と補足）を組み立てる。
    - triggers.any_keywords に合致しない場合は None
    - text_normalizers / extractors / date_rules / query_templates / hint_notes を順に適用
    """
    cfg = load_intent_config(intent_name, locale)

    # 1) trigger
    kws = (cfg.get("triggers", {}) or {}).get("any_keywords", []) or []
    if not any(k in (user_text or "") for k in kws):
        return None

    # 2) 前処理
    norm_steps = cfg.get("text_normalizers", []) or []
    norm_text = _apply_text_normalizers(user_text, norm_steps) if norm_steps else (user_text or "")

    # 3) 抽出（city など）
    fields = _extract_fields(norm_text,
                             cfg.get("extractors", []) or [],
                             cfg.get("aliases", {}) or {})

    # 4) 相対日付 → 具体日付の配列
    dates = _resolve_dates(norm_text, cfg.get("date_rules", []) or [])
    flags = {
        "has_city": bool(fields.get("city")),
        "has_date": bool(dates),
    }

    # 5) クエリ生成（条件に合う最初のブロック）
    qs: List[str] = []
    max_q = int(cfg.get("max_queries", 3))
    for block in cfg.get("query_templates", []) or []:
        when = block.get("when", {}) or {}
        if all(flags.get(k) == v for k, v in when.items()):
            templates = block.get("queries", []) or []
            if flags["has_date"] and dates:
                for dt in dates[:2]:
                    for t in templates:
                        qs.append(t.format(date_ja=_fmt_date_jp(dt), **fields))
                        if len(qs) >= max_q:
                            break
                    if len(qs) >= max_q:
                        break
            else:
                for t in templates:
                    qs.append(t.format(date_ja="", **fields))
                    if len(qs) >= max_q:
                        break
        if len(qs) >= max_q:
            break

    if not qs:
        return None

    # 6) ヒント文の構築
    hint = f"WEB検索ヒント（{intent_name}）:\n- queries:\n"
    for i, q in enumerate(qs, 1):
        hint += f"  {i}) {q}\n"
    for note in (cfg.get("hint_notes", []) or []):
        hint += f"- {note}\n"

    return hint


def build_tool_hint_auto(user_text: str,
                         locale: str = "ja",
                         prefer_order: List[str] | Tuple[str, ...] | None = None) -> Optional[str]:
    """
    インテントを自動判定し、最初にヒットした intent でヒント文字列を返す。
    prefer_order を与えるとその順で優先探索。
    """
    candidates = tuple(prefer_order) if prefer_order else list_intent_names(locale)
    for name in candidates:
        hint = build_tool_hint_from_config(name, user_text, locale)
        if hint:
            return hint
    return None
