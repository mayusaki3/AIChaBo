# 送信・ログ直前に「秘匿情報をマスク」するためのラッパ
# - redact() は共通I/O側のパターンマッチでAPIキー等を伏せ字化
# - exp_lines は「あとでまとめて出す用の簡易バッファ」（必要に応じて利用）
from common.utils.redact import redact
ANSI_RE = __import__("re").compile(r"\x1b\[[0-9;]*m")
exp_lines: list[str] = []

def _print(msg: str, printmsg: bool = True, expmsg: bool = False):
    """安全なprint。常に redact を通してから出力/保存する。"""
    safe = redact(str(msg or ""))
    if printmsg:
        print(safe)
    if expmsg:
        # エクスポート用には ANSI シーケンスを落としてプレーン化
        exp_lines.append(ANSI_RE.sub("", safe))
