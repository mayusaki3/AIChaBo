# common/chat/chat_core.py
# ------------------------------------------------------------
# chat_core: 1回分の送受信の最小ユニット。
# 目的:
#  - chat_loop の“外側の流れ”から切り離し、1ターン送信の責務を集約
#  - T04-01 では provider/model の必須チェックと「文字列を返す」ことのみ保証
# 設計方針:
#  - 依存（プロバイダ実装/API呼び出し）は将来の拡張ポイントとし、当面は echo 応答
#  - 上位(chat_loop等)で policy 補完やAPIキー解決を済ませた context を受ける前提
# ------------------------------------------------------------
from typing import Any, Callable, Dict, Optional

def _require_non_empty_str(val: Optional[str], name: str) -> str:
    """
    必須フィールドの共通チェック: None/空/空白のみを拒否し、stripした値を返す。
    """
    s = (val or "").strip()
    if not s:
        raise ValueError(f"{name} is required")
    return s

def send_once(
    *,
    text: str,
    context: Dict[str, Any],
    chat_fn: Optional[Callable[..., str]] = None,
) -> str:
    """
    1回分の送受信（最小コア）。
    - 必須: context['provider'], context['model'] は非空文字列
    - 現時点: 実際のAPI呼び出しは行わず、chat_fn未指定なら echo を返す
    将来拡張:
    - chat_fn をプロバイダごとの送信関数に差し替え可能（DI）
    """
    # 入力ガード（空文字や空白のみは上位 chat_loop で弾く想定だが、二重化しても安全）
    if not isinstance(text, str) or not text.strip():
        # T04-01 では厳密値を返す要件は無いので、例外or既定応答どちらでも可。
        # ここでは例外にする（テスト側は例外/None/strのいずれでもPASS扱い）
        raise ValueError("text is empty")

    # 必須チェック
    provider = _require_non_empty_str(context.get("provider"), "chat.provider")
    model    = _require_non_empty_str(context.get("model"),    "chat.model")

    # ここで provider/model の正規化を入れる拡張余地あり（必要なら provider.normalize）

    # 送信関数: 指定がなければ echo を返す最小実装（T04-01 を通す目的）
    if chat_fn is None:
        # echo 応答（テストは「strであること」のみを検証）
        return text.strip()

    # 将来: 実プロバイダ関数に委譲（例: chat_fn(context_list=[text], api_key=..., model=model) など）
    # ここでは最小責務の確認だけ行い、未知の引数は渡さない（必要に応じて拡張）
    return chat_fn(text=text, provider=provider, model=model)
