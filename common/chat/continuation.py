# common/chat/continuation.py
# -*- coding: utf-8 -*-
"""
チャット継続（Continuation）ユーティリティ

想定仕様（T07-01 / T07-02 テスト準拠）:

- 公開API:
    continue_chat(messages, policy=None) -> str

- テスト側からの前提:
    - tests では `from common.chat import continuation as C` し、
      `cls.cont = C.continue_chat` としている。
    - `C.chat_loop` / `C.textsplit` / `C.normalize_messages`
      を patch.object するテストが存在する。
      → 本モジュール側で **同名属性をモジュール直下に用意** する必要がある。

- 動作要件（テストから読み取れる範囲）:

  [共通]
  - messages が空のときは何もせずに "" を返す（chat 不呼び出し）
    → T07-01-01
  - 例外は握りつぶして "" を返す（ログ出力などは本実装で対応可）
    → T07-01-03, T07-02-03 など
  - `normalize_messages(messages)` を経由してから chat に渡す
    → T07-01-06 で normalize_messages が呼ばれることを確認
  - `chat_loop.chat(messages=..., policy=...)` を呼び出す
    （policyに chat_fn が無い通常ケース）
    → T07-01-02 など
  - policy に "chat_fn" があれば、それを優先して使用する
    → T07-01-05 「policy 直呼び」

  [max_steps 関連]
  - policy["max_steps"] が 0 以下なら chat は 1度も呼ばれない
    → T07-02-01

  [textsplit 関連]
  - 長文の場合は textsplit で「最後のテキスト」を分割し、
    分割されたチャンクごとに chat を呼び出して結果を連結する
    → T07-01-04 長文継続（分割）: 最終返却文字列が "part2" で終わることを確認
  - policy["max_steps"] が指定されている場合、その回数を上限に
    チャンクごとの chat 呼び出しを行う
    → T07-01-07
  - textsplit が空配列や空文字だけを返した場合、chat は呼ばれない
    → T07-02-02 空チャンク → 呼ばれない
  - textsplit が例外を投げた場合、chat は呼ばれない（"" を返す）
    → T07-02-03
  - 単一チャンクのときは chat は 1回だけ呼ばれる
    → T07-02-05

  [policy=None]
  - policy が None でも落ちずに動作する
    → T07-02-04

  [戻り値]
  - 通常ケース（例外無し）のとき、
    - 単一呼び出しなら chat_fn の戻り値（str）をそのまま返す（"pong" / "ok" 等）
      → T07-01-02, T07-01-05
    - 複数チャンク呼び出しなら、各 call の戻り値（str）を連結して返す
      → T07-01-04 ("...part2" で終わること)

  [その他]
  - chat_fn が None を返したら、その時点で終了（以降のチャンクは処理しない）
    → T07-01-08
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union

# ----------------------------------------------------------------------
# textsplit ラッパ
# ----------------------------------------------------------------------

try:
    # 既存の sentence/固定長分割ロジック
    from common.chat.textsplit import split_text as _split_text  # type: ignore[import]
except Exception:  # pragma: no cover - フォールバック（テストでは patch される）
    def _split_text(text: str, max_chars: int, split_sentences: bool = False) -> List[str]:
        """ごく簡易なフォールバック実装。"""
        if not text:
            return []
        if max_chars <= 0:
            raise ValueError("max_chars must be > 0")
        # 固定長スライスのみ
        return [text[i : i + max_chars] for i in range(0, len(text), max_chars)]


def textsplit(text: str, max_chars: int, split_sentences: bool = False) -> List[str]:
    """
    モジュール直下に公開する textsplit。
    テスト側では `patch.object(C, "textsplit", ...)` される前提。
    """
    return _split_text(text, max_chars=max_chars, split_sentences=split_sentences)  # type: ignore[arg-type]


# ----------------------------------------------------------------------
# chat_loop ラッパ
# ----------------------------------------------------------------------

@dataclass
class _ChatLoop:
    """
    実際の実装ではストリーミング／リトライなどを担う想定。
    テストでは patch.object で chat メソッドが置き換えられる。
    """

    def chat(self, *, messages: Sequence[Any], policy: Dict[str, Any]) -> Optional[str]:
        """
        フォールバック（実運用では別実装に差し替え）。
        テストでは常にモックされるため、この中身は基本的に通らない。
        """
        # 何も返さないデフォルト
        return None


# テストから patch される公開インスタンス
chat_loop = _ChatLoop()


# ----------------------------------------------------------------------
# メッセージ正規化
# ----------------------------------------------------------------------

def normalize_messages(messages: Any) -> List[Any]:
    """
    メッセージ正規化処理。
    - 実装の本体は別モジュールに切り出す前提だが、
      T07 では「この関数が呼ばれること」だけを検証している。
    """
    if messages is None:
        return []
    if isinstance(messages, list):
        return list(messages)
    # 単一要素はリストに包む
    return [messages]


# ----------------------------------------------------------------------
# 内部ユーティリティ
# ----------------------------------------------------------------------

def _select_chat_fn(policy: Optional[Dict[str, Any]]) -> Callable[..., Optional[str]]:
    """
    policy から chat_fn を選択。
    - policy["chat_fn"] が callable ならそれを優先
    - それ以外は chat_loop.chat を使う
    """
    if policy and callable(policy.get("chat_fn")):
        # policy 直呼び
        chat_fn = policy["chat_fn"]  # type: ignore[assignment]
        # テストの都合上、引数は (messages=..., policy=...) で呼ぶ前提
        return chat_fn  # type: ignore[return-value]
    # デフォルト: chat_loop.chat
    return chat_loop.chat  # type: ignore[return-value]


def _extract_last_text(messages: List[Any]) -> Tuple[List[Any], Optional[str], Optional[Any]]:
    """
    メッセージ列の「最後のテキスト」と「プレフィックス」を取り出す。

    戻り値:
        prefix_messages: 最後の要素を除いた部分
        last_text:       最後のテキスト（str に変換） / テキストが無ければ None
        last_raw:        最後の元オブジェクト（dict 等）/ 無ければ None

    - 最後の要素が dict かつ "content" を持つ場合: content をテキストと見なす
    - それ以外は、その要素を str() したものをテキストと見なす
    """
    if not messages:
        return [], None, None

    prefix = messages[:-1]
    last = messages[-1]

    # dict 形式の { "role": "...", "content": "..." } を想定
    if isinstance(last, dict) and "content" in last:
        return prefix, str(last["content"]), last

    # 文字列その他はそのままテキスト扱い
    return prefix, str(last), last


def _rebuild_messages_for_chunk(
    prefix: List[Any],
    last_raw: Any,
    chunk: str,
) -> List[Any]:
    """
    チャンクごとのメッセージ列を再構築する。
    - 最後の要素が dict なら content だけ差し替え
    - それ以外なら単純に prefix + [chunk]
    """
    if isinstance(last_raw, dict):
        new_last = dict(last_raw)
        new_last["content"] = chunk
        return prefix + [new_last]
    # 文字列など
    return prefix + [chunk]


# ----------------------------------------------------------------------
# メインAPI: continue_chat
# ----------------------------------------------------------------------

def continue_chat(messages: Any, policy: Optional[Dict[str, Any]] = None) -> str:
    """
    チャット継続のメインエントリ。

    引数:
        messages:
            - list[dict] / list[str] / str など
            - T07 テストでは主に list[dict] or list[str]
        policy:
            - provider/model/max_steps/chat_fn などのパラメータを含む dict or None

    戻り値:
        - 通常ケース: 各 chat 呼び出しの戻り値（str）を連結した文字列
        - エラー時   : ""（空文字）
    """
    # policy None ガード
    if policy is None:
        policy = {}

    # 空メッセージは即終了（chat 呼び出し無し）
    if not messages:
        return ""

    # max_steps 判定（0 以下なら一切呼ばない）
    max_steps_raw = policy.get("max_steps")
    if isinstance(max_steps_raw, int) and max_steps_raw <= 0:
        return ""

    # メッセージ正規化（テストでは normalize_messages が呼ばれることを確認）
    norm_messages = normalize_messages(messages)

    # 再度、空になった場合も安全側で終了
    if not norm_messages:
        return ""

    # チャット関数選択（policy.chat_fn 優先）
    chat_fn = _select_chat_fn(policy)

    # 最後のテキストを抽出
    prefix, last_text, last_raw = _extract_last_text(norm_messages)
    if last_text is None or last_raw is None:
        # テキスト相当が見つからなければ、そのまま 1 回だけ呼んで結果を返す
        try:
            reply = chat_fn(messages=norm_messages, policy=policy)
        except Exception:
            return ""
        return reply or ""

    # textsplit でチャンク化
    # max_chars は policy["max_chars"] があれば使用、無ければ len(last_text)
    max_chars = policy.get("max_chars")
    if not isinstance(max_chars, int) or max_chars <= 0:
        max_chars = len(last_text) if last_text else 1

    try:
        chunks = textsplit(last_text, max_chars=max_chars, split_sentences=False)
    except Exception:
        # T07-02-03: textsplit 例外時は chat を呼ばず "" を返す
        return ""

    # 空チャンクや空文字は除去
    chunks = [c for c in chunks if isinstance(c, str) and c != ""]
    if not chunks:
        # T07-02-02: 空チャンクなら chat を呼ばない
        return ""

    # max_steps
    max_steps: Optional[int] = max_steps_raw if isinstance(max_steps_raw, int) else None

    # 各チャンクごとに chat を呼び出し、結果を連結
    out_parts: List[str] = []
    steps = 0

    for chunk in chunks:
        if max_steps is not None and steps >= max_steps:
            break

        step_messages = _rebuild_messages_for_chunk(prefix, last_raw, chunk)

        try:
            reply = chat_fn(messages=step_messages, policy=policy)
        except Exception:
            # 例外は握り潰して終了（T07-01-03 想定）
            break

        # None の場合はそれ以上続けない（T07-01-08）
        if reply is None:
            break

        # str 以外が返ってきた場合は文字列化しておくが、
        # テストでは基本 str なのでこの分岐は通らない想定
        if not isinstance(reply, str):
            reply = str(reply)

        out_parts.append(reply)
        steps += 1

    # 1回も返却が無ければ空文字
    if not out_parts:
        return ""

    # 連結して返却
    return "".join(out_parts)
