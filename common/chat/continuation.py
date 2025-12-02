"""
common.chat.continuation

チャットの「継続実行」（長文の分割送信など）を行うユーティリティ。

・textsplit.split_text を使って入力テキストをチャンクに分割
・max_steps までチャンクを順番に送信
・policy["chat_fn"] があればそれを優先して呼び出し
・例外は握り潰してログ出力のみ行い、返り値は空文字列にする
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

# テストから patch 対象になるため、モジュールレベルに import しておく
from common.chat import chat_loop  # type: ignore[import]
from common.chat import message    # type: ignore[import]
from common.chat import textsplit  # type: ignore[import]


# 型エイリアス（簡易）
ChatMessages = Any
Policy = Optional[Dict[str, Any]]
ChatFn = Callable[..., Any]


def _resolve_policy(policy: Policy) -> Dict[str, Any]:
    """
    policy が None の場合にも安全に扱えるよう、dict に正規化する。

    Args:
        policy: チャット実行ポリシー。None も許容する。

    Returns:
        dict に正規化した policy。
    """
    if policy is None:
        return {}
    if not isinstance(policy, dict):
        # 想定外の型の場合も、落ちないように空 dict を返す
        return {}
    return policy


def _resolve_chat_fn(policy: Dict[str, Any]) -> ChatFn:
    """
    policy から使用するチャット関数を決定する。

    優先順:
      1. policy["chat_fn"] が callable ならそれを使う
      2. それ以外は chat_loop.chat を使う

    Args:
        policy: 正規化済み policy dict

    Returns:
        呼び出しに使用するチャット関数。
    """
    chat_fn = policy.get("chat_fn")
    if callable(chat_fn):
        # 直指定の関数を優先（T07-01-05）
        return chat_fn

    # デフォルトは共通チャットループ
    return chat_loop.chat  # type: ignore[return-value]


def _normalize_messages(messages: ChatMessages) -> ChatMessages:
    """
    メッセージの正規化。

    ・list の場合: そのまま返す（すでに正規化されている前提）
    ・list 以外の場合: message.normalize_messages に委譲する

    T07-01-06 で message.normalize_messages が呼ばれることを期待しているため、
    「非 list 入力」のときは必ず normalize_messages を通す。
    """
    if isinstance(messages, list):
        return messages
    # list 以外は normalize_messages に委譲
    return message.normalize_messages(messages)  # type: ignore[no-any-return]


def _extract_tail_text(messages: ChatMessages) -> str:
    """
    チャンク分割対象となるテキストを抽出する。

    ここでは「最後のメッセージの内容」を対象とする。

    対応パターン:
      ・messages[-1] が dict で "content" キーを持つ場合
      ・messages[-1] が str の場合

    Args:
        messages: 正規化済みメッセージ（list またはそれに準ずるもの）

    Returns:
        抽出したテキスト。取得できない場合は空文字列。
    """
    try:
        if not isinstance(messages, list) or not messages:
            return ""
        last = messages[-1]
        if isinstance(last, dict):
            content = last.get("content")
            if isinstance(content, str):
                return content
        if isinstance(last, str):
            return last
    except Exception:
        # 想定外の構造でも落とさない
        return ""
    return ""


def _split_into_chunks(text: str) -> Optional[List[str]]:
    """
    入力テキストをチャンク（分割テキスト）に変換する。

    ・空文字列の場合は空リストを返す
    ・textsplit.split_text の返り値が
        - dict の場合: result["chunks"] を想定
        - list / tuple の場合: そのままチャンク列として扱う
        - それ以外: テキスト全体を 1 チャンクとして扱う
    ・textsplit.split_text が例外を投げた場合:
        - 例外を握り潰してログ出力し、None を返す
          （呼び出し側で「チャット関数を呼ばない」判断に使う）

    戻り値:
        - 正常系: チャンク文字列のリスト（空リストを含む）
        - 例外発生時: None
    """
    if not text:
        return []

    try:
        result = textsplit.split_text(text)  # type: ignore[attr-defined]
    except Exception:  # pragma: no cover - ログのみ
        print("textsplit.split_text failed in continuation.")
        import traceback
        traceback.print_exc()
        # エラー発生を呼び出し側で判別できるよう None
        return None

    chunks: List[str]

    # dict 形式（{"chunks": [...]}）を優先的に解釈
    if isinstance(result, dict) and "chunks" in result:
        raw = result.get("chunks")
        if isinstance(raw, (list, tuple)):
            chunks = [c for c in raw if isinstance(c, str) and c]
        else:
            chunks = []
    # list / tuple の場合はそのまま
    elif isinstance(result, (list, tuple)):
        chunks = [c for c in result if isinstance(c, str) and c]
    else:
        # 不明な形式の場合は、丸ごと 1 チャンクとして扱う
        if isinstance(result, str) and result:
            chunks = [result]
        else:
            chunks = [text]

    return chunks


def _prepare_step_messages(base_messages: ChatMessages, chunk: str) -> ChatMessages:
    """
    1 ステップ分のメッセージを構築する。

    ・基本方針:
      - base_messages を shallow copy し、最後の要素をチャンクに置き換える
      - 最後の要素が dict の場合は "content" を書き換える
      - 最後の要素が str の場合は、その要素自体を置き換える

    Args:
        base_messages: 正規化済みメッセージ
        chunk: 今回送信するテキストチャンク

    Returns:
        今回のチャット呼び出しに渡すメッセージ列。
    """
    # list でない場合は、そのまま chunk を渡すしかない
    if not isinstance(base_messages, list) or not base_messages:
        return [chunk]

    step_msgs = list(base_messages)
    last = step_msgs[-1]

    # dict: content を差し替え
    if isinstance(last, dict):
        new_last = dict(last)
        new_last["content"] = chunk
        step_msgs[-1] = new_last
        return step_msgs

    # str: 要素を文字列チャンクに差し替え
    if isinstance(last, str):
        step_msgs[-1] = chunk
        return step_msgs

    # 想定外の型: 一旦そのまま + 末尾にチャンクを追加
    step_msgs.append(chunk)
    return step_msgs


def continue_chat(*, messages: ChatMessages, policy: Policy) -> str:
    """
    チャットの継続実行を行うメイン関数。

    テストからは次の点が期待されている:

    - [T07-01-01] messages=[] / policy={} の場合は "" を返し、チャット関数は呼ばない
    - [T07-01-02] 通常ケースでは 1 回だけチャット関数を呼び、その返り値をそのまま返す
    - [T07-01-03] チャット関数が例外を投げた場合は例外を握り潰し、空文字列を返す
    - [T07-01-04] 長文分割ではチャンク数回だけチャット関数を呼び、結合結果を返す（末尾が "part2"）
    - [T07-01-05] policy["chat_fn"] があれば chat_loop.chat ではなくそれを使う
    - [T07-01-06] messages が list 以外の場合は message.normalize_messages を呼ぶ
    - [T07-01-07] max_steps により実際の呼び出し回数が制限される
    - [T07-01-08] チャット関数の返り値が None の場合は結果に含めない（空文字列）

    - [T07-02-01] max_steps=0 の場合はチャット関数を 1 回も呼ばない
    - [T07-02-02] 空チャンク（_split_into_chunks の戻り値が []）なら
                  → 元のテキスト1チャンクとしてチャット関数を 1 回だけ呼ぶ
    - [T07-02-03] textsplit.split_text が例外の場合（_split_into_chunks が None）
                  → チャット関数は呼ばない
    - [T07-02-04] policy=None でも例外を出さない
    - [T07-02-05] 単一チャンクならチャット関数は 1 回だけ呼ばれる

    Args:
        messages: チャットメッセージ。list または文字列など。
        policy: チャット実行ポリシー。None 許容。

    Returns:
        チャット結果のテキスト（結合後）。何も得られなかった場合は ""。
    """
    # 1) policy 正規化
    policy_dict = _resolve_policy(policy)

    # 2) 空メッセージは即終了（T07-01-01）
    if not messages:
        return ""

    # 3) チャット関数の決定（policy["chat_fn"] 優先、T07-01-05）
    chat_fn = _resolve_chat_fn(policy_dict)

    # 4) メッセージ正規化（T07-01-06）
    norm_messages = _normalize_messages(messages)

    # 5) 分割対象テキストの抽出
    tail_text = _extract_tail_text(norm_messages)

    # 末尾テキストが空なら何も送るものがない → チャット関数は呼ばない（T07-02-02）
    if not tail_text:
        return ""

    # 6) チャンク分割
    chunks_or_none = _split_into_chunks(tail_text)

    # textsplit 側で例外発生など → チャット関数は呼ばない（T07-02-03）
    if chunks_or_none is None:
        return ""

    chunks = chunks_or_none

    # 分割結果が空リストの場合:
    # 正常系では「分割する必要がなかった」ケースとして扱い、
    # 元のテキスト1チャンクで送信する（T07-01-02, 05, 06, 08 / T07-02-02）
    if not chunks:
        chunks = [tail_text]

    # 7) ステップ上限
    max_steps_raw = policy_dict.get("max_steps")
    try:
        max_steps = int(max_steps_raw) if max_steps_raw is not None else len(chunks)
    except (TypeError, ValueError):
        max_steps = len(chunks)

    # max_steps <= 0 の場合は呼び出さない（T07-02-01）
    if max_steps <= 0:
        return ""

    # 8) 実行ループ
    responses: List[str] = []
    steps = 0

    for chunk in chunks:
        if steps >= max_steps:
            break

        step_msgs = _prepare_step_messages(norm_messages, chunk)

        try:
            # chat_fn は messages / policy キーワード引数で呼び出す
            reply = chat_fn(messages=step_msgs, policy=policy_dict)
        except Exception:
            # T07-01-03: 例外は握り潰し、結果には反映しない
            steps += 1
            continue

        if not reply:
            # None / 空文字列などはスキップ（T07-01-08）
            steps += 1
            continue

        if isinstance(reply, str):
            responses.append(reply)
        else:
            try:
                responses.append(str(reply))
            except Exception:
                # 文字列化できない場合は無視
                pass

        steps += 1

    # 9) すべて結合して返す
    if not responses:
        return ""
    return "".join(responses)
